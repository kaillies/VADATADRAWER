# Q1: What is the output of the following code?
```
info = """"
50 Nanyang Avenue, 
Singapore 639798
Tel: 6791 1744
"""
s1 = re.sub(r'[^\w\s]','', info)
s2 = s1.lower()
s3 = re.sub(r'.p.*e', 'sg', s2)
s4 = re.sub(r'\d+', '', s3)
s5 = re.sub(r'\s+','', s3)
```
```
1. s1 =  
50 Nanyang Avenue 
Singapore 639798
Tel: 6791 1744
2. s2 = 
50 nanyang avenue 
singapore 639798
tel: 6791 1744
3. s3 = 
50 nanyang avenue 
sinsg 639798
tel 6791 1744
4. s4 =
 nanyang avenue 
singsg 
tel  
5. s5 = 50nanyangavenuesingapore639798tel67911744
```
# Q2: What is the missing code to break the text into words without splitting words and punctuation marks?
```
text = 'The quick brown fox jumps over the lazy dog. The dog slept over the veranda. The fox chased the rabbit. The rabbit ran away.'
sentence_tokens = ???
```
```
1. sentence_tokens = sent_tokenize(text)
2. sentence_tokens = word_tokenize(text)
3. sentence_tokens = text.split()
4. sentence_tokens = text.split('.')
5. sentence_tokens = text.split('?')
```
# Q3: What is the output of the following code?
```
words = ["running", "runner", "ran", "easily", "fairness", "isn't"]
stemmer = PorterStemmer()
stemmed_words = [stemmer.stem(word) for word in words]
print(stemmed_words)
```
```
1. ['run', 'runner', 'run', 'easily', 'fairness', "isn't"]
2. ['running', 'runner', 'ran', 'easili', 'fairness', "is not"]
3. ['run', 'runner', 'run', 'easily', 'fair', "isn't"]
4. ['run', 'runner', 'ran', 'easily', 'fair', "is not"]
5. ['run', 'runner', 'ran', 'easili', 'fair', "isn't"] 
```
# Q4: What is the output of the following code?
```
words = ["running", "runner", "ran", "easily", "fairness", "isn't"]
lemmatizer = WordNetLemmatizer()
lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in words]
print(lemmatized_words)
```
```
1. ['run', 'runner', 'run', 'easily', 'fairness', "isn't"]
2. ['running', 'runner', 'ran', 'easili', 'fairness', "is not"]
3. ['run', 'runner', 'run', 'easily', 'fair', "isn't"]
4. ['run', 'runner', 'ran', 'easily', 'fair', "is not"]
5. ['run', 'runner', 'ran', 'easili', 'fair', "isn't"] 
```
# Q5: What is the output of the following code?
```
text = 'The quick brown fox jumps over the lazy dog'
n = 2
def generate_ngrams(text, n):
    words = text.split()
    ngrams = zip(*[words[i:] for i in range(n)])
    return [' '.join(ngram) for ngram in ngrams]
print(generate_ngrams(text, n))
```
```
1. ['The', 'quick', 'brown', 'fox', 'jumps', 'over', 'the', 'lazy', 'dog']
2. ['The quick', 'brown fox', 'jumps over', 'the lazy dog']
3. ['The quick brown', 'brown fox jumps', 'jumps over the', 'the lazy dog']
4. ['The quick', 'brown fox', 'jumps over', 'the lazy', 'lazy dog']
5. ['The quick', 'quick brown', 'brown fox', 'fox jumps', 'jumps over', 'over the', 'the lazy', 'lazy dog']
```