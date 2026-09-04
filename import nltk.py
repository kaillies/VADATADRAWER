import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer

# 下载必要资源
nltk.download('wordnet')
nltk.download('punkt')
nltk.download('omw-1.4')

# 构造数据
reference = "The cat sat on the mat."
candidate_good = "The cat sat on the mat."
candidate_medium = "The cat is sitting on the mat."
candidate_poor = "A dog lay near the rug."

ref_tokens = reference.split()
cand_good_tokens = candidate_good.split()
cand_medium_tokens = candidate_medium.split()
cand_poor_tokens = candidate_poor.split()

# 1. ROUGE
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
print("=== ROUGE-L ===")
for name, cand in [("Good", candidate_good), ("Medium", candidate_medium), ("Poor", candidate_poor)]:
    s = scorer.score(reference, cand)
    print(f"{name}: ROUGE-L F1 = {s['rougeL'].fmeasure:.4f}")

# 2. BLEU
smoothie = SmoothingFunction().method4
print("\n=== BLEU ===")
print(f"Good:   {sentence_bleu([ref_tokens], cand_good_tokens, smoothing_function=smoothie):.4f}")
print(f"Medium: {sentence_bleu([ref_tokens], cand_medium_tokens, smoothing_function=smoothie):.4f}")
print(f"Poor:   {sentence_bleu([ref_tokens], cand_poor_tokens, smoothing_function=smoothie):.4f}")

# 3. METEOR
print("\n=== METEOR ===")
print(f"Good:   {meteor_score([ref_tokens], cand_good_tokens):.4f}")
print(f"Medium: {meteor_score([ref_tokens], cand_medium_tokens):.4f}")
print(f"Poor:   {meteor_score([ref_tokens], cand_poor_tokens):.4f}")