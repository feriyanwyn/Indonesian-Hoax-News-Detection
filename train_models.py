import os
import re
import html
import argparse
import numpy as np
import pandas as pd
import joblib
from bs4 import BeautifulSoup

import torch
import nltk
from tqdm.auto import tqdm

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

from transformers import AutoTokenizer, AutoModel

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    confusion_matrix,
    precision_recall_fscore_support
)

# Download required NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

class HoaxPreprocessor:
    def __init__(self):
        print("Setting up Sastrawi & BeautifulSoup cleaning tools...")
        self.stemmer = StemmerFactory().create_stemmer()
        self.stopwords = StopWordRemoverFactory().get_stop_words()

    def scrub_html(self, text):
        """Robustly remove HTML tags, scripts, and unescape entities."""
        if not isinstance(text, str) or not text:
            return ""

        # 1. Unescape HTML entities (e.g., &nbsp; -> space, &amp; -> &)
        text = html.unescape(text)

        # 2. Use BeautifulSoup to remove tags and dangerous content (scripts/styles)
        soup = BeautifulSoup(text, "html.parser")
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.decompose()

        # Get text with space separator to avoid word merging
        clean_text = soup.get_text(separator=" ")

        # 3. Remove leftover HTML tags if any
        clean_text = re.sub(r'<.*?>', '', clean_text)

        return clean_text

    def clean_text(self, text, mode='natural'):
        """Normalize and clean Indonesian text.
        'natural' mode is for Transformers (IndoBERT).
        'stemmed' mode is for traditional ML (Naive Bayes).
        """
        if not isinstance(text, str):
            return ""

        # Step 1: Remove HTML/JS Noise
        text = self.scrub_html(text)

        # Step 2: Lowercasing
        text = text.lower()

        # Step 3: DATA LEAKAGE PREVENTION
        leakage_patterns = r'\[hoaks\]|\[fakta\]|cek fakta:?|infografik:?|benarkah:?'
        text = re.sub(leakage_patterns, '', text).strip()

        # Step 4: Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)

        # Step 5: Clean special chars but keep basic punctuation for BERT
        if mode == 'natural':
            text = re.sub(r'[^a-z0-9\s.,!?]', '', text)
        else:
            text = re.sub(r'[^a-z\s]', '', text)

        text = re.sub(r'\s+', ' ', text).strip()

        if mode == 'natural':
            return text

        # Classical Preprocessing (Only for non-transformer models)
        tokens = nltk.tokenize.word_tokenize(text)
        tokens = [t for t in tokens if t not in self.stopwords]
        processed = " ".join(tokens)
        return self.stemmer.stem(processed)

    def process_dataframe(self, df, sample_size=None):
        """Clean dataset and generate processed text column."""
        # Drop rows with missing values
        df = df.dropna(subset=["NARRATIVE", "TITLE", "LABEL"])
        df = df.drop_duplicates(subset=["NARRATIVE", "TITLE"])

        if sample_size and sample_size < len(df):
            df = df.sample(n=sample_size, random_state=42)
        else:
            df = df.copy()

        print("Running preprocessing pipeline...")
        df["clean_combined"] = (
            df["TITLE"] + ". " + df["NARRATIVE"]
        ).apply(lambda x: self.clean_text(x, mode='natural'))

        return df

def extract_embeddings(text_list, model_name="indobenchmark/indobert-base-p1", batch_size=16):
    """Generate semantic embeddings for a list of texts using IndoBERT."""
    # Load tokenizer and transformer model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    # Determine computing device
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    print(f"Using device for embedding extraction: {device}")

    model.to(device)
    model.eval()

    all_embeddings = []

    # Process data in batches
    for start in tqdm(range(0, len(text_list), batch_size), desc="Generating Embeddings"):
        batch_texts = text_list[start:start + batch_size].tolist()

        encoded_inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            model_outputs = model(**encoded_inputs)

        # Attention mask for valid token weighting
        attention_mask = encoded_inputs["attention_mask"].unsqueeze(-1).expand(
            model_outputs.last_hidden_state.size()
        ).float()

        # Mean pooling over token embeddings
        weighted_sum = torch.sum(model_outputs.last_hidden_state * attention_mask, dim=1)
        mask_sum = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
        sentence_embeddings = (weighted_sum / mask_sum).cpu().numpy()

        all_embeddings.append(sentence_embeddings)

    return np.vstack(all_embeddings)

def main():
    parser = argparse.ArgumentParser(description="Train Hoax Detection Models using IndoBERT features.")
    parser.add_argument("--data_file", type=str, default="dataset_clean.csv", help="Path to input clean CSV dataset.")
    parser.add_argument("--sample_limit", type=int, default=None, help="Limit number of samples for fast training/validation.")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size for generating embeddings.")
    parser.add_argument("--output_dir", type=str, default="models", help="Directory to save trained models and scaler.")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Load Dataset
    print(f"Loading {args.data_file}...")
    if not os.path.exists(args.data_file):
        raise FileNotFoundError(f"Dataset file '{args.data_file}' not found. Please check the path.")
    
    raw_data = pd.read_csv(args.data_file, encoding='utf-8', sep=',', quotechar='"', on_bad_lines='skip')
    print(f"Successfully loaded raw data: {len(raw_data)} records.")

    # 2. Preprocess Data
    text_processor = HoaxPreprocessor()
    processed_data = text_processor.process_dataframe(raw_data, sample_size=args.sample_limit)
    print(f"Processed dataset: {len(processed_data)} valid records.")

    # 3. Extract Embeddings
    features = extract_embeddings(processed_data["clean_combined"], batch_size=args.batch_size)
    labels = processed_data["LABEL"].to_numpy()

    # 4. Split dataset into training and testing sets (90/10 split)
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.1,
        random_state=42
    )
    print(f"\nDataset split: {len(X_train_raw)} training samples and {len(X_test_raw)} test samples.")

    # 5. Fit Scaling (StandardScaler)
    print("Fitting StandardScaler on embeddings...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    # 6. Initialize models
    models = {
        "SVM (Linear)": SVC(kernel='linear', probability=True, class_weight='balanced'),
        "Random Forest": RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42),
        "Naive Bayes": GaussianNB()
    }

    # Train and evaluate models
    trained_models = {}
    for model_name, clf in models.items():
        print(f"\n" + "="*50)
        print(f" Training: {model_name} ")
        print("="*50)

        # Train model
        clf.fit(X_train, y_train)
        trained_models[model_name] = clf

        # Predict test data
        y_pred = clf.predict(X_test)

        # Compute metrics
        acc_score = accuracy_score(y_test, y_pred)
        f1_weighted = f1_score(y_test, y_pred, average="weighted")
        precision, recall, _, _ = precision_recall_fscore_support(y_test, y_pred, labels=[0])

        print(f"Overall Accuracy  : {acc_score:.6f}")
        print(f"Weighted F1-Score : {f1_weighted:.4f}")
        print(f"Hoax Detection (Recall)    : {recall[0]:.4f} (Target for catching hoaxes)")
        print(f"Hoax Detection (Precision) : {precision[0]:.4f} (Reliability of hoax flags)")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=["Hoax (0)", "Fact (1)"]))

    # 7. Serialize models and scaler
    print(f"\nSaving models and scaler to directory: {args.output_dir}...")
    joblib.dump(scaler, os.path.join(args.output_dir, "scaler.joblib"))
    joblib.dump(trained_models["SVM (Linear)"], os.path.join(args.output_dir, "model_svm.joblib"))
    joblib.dump(trained_models["Random Forest"], os.path.join(args.output_dir, "model_rf.joblib"))
    joblib.dump(trained_models["Naive Bayes"], os.path.join(args.output_dir, "model_nb.joblib"))
    print("All artifacts successfully saved! Model training is complete.")

if __name__ == "__main__":
    main()
