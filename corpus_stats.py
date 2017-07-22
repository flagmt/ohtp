"""
Mike Taylor
July 2017
calculate number of words, word frequencies and other stats for corpus
"""
import nltk
import itertools


tagged_path = r'C:\Users\met28\OneDrive - Northern Arizona University\Shared with Everyone\tagged'
# use "'corpus'" instead of tagged_path to process just those files that have been reviewed
oh_corpus = nltk.corpus.PlaintextCorpusReader(tagged_path,
                                              '.*\.txt',
                                              encoding='latin-1',
                                              word_tokenizer=nltk.WhitespaceTokenizer())
file_names = oh_corpus.fileids()


#############################################
# locate and print toponyms found in corpus
all_topos = []
topo = []
num_topos = 0
for word in oh_corpus.words():
    if not topo:
        if not word.startswith('<'):
            continue
        else:
            topo.append(word[1:].strip(','))
            if word.endswith(','):
                # print(*topo, sep=' ')
                num_topos = num_topos + 1
                all_topos.append(topo)
                topo = []
                continue
    else:
        topo.append(word.strip(','))
        if word.endswith(','):
            # print(*topo, sep=' ')
            num_topos = num_topos + 1
            all_topos.append(topo)
            topo = []
            continue

num_words = len(oh_corpus.words())
print('Number of words in corpus: ', num_words)
print('number of topos: ', num_topos)
all_topos.sort()
unique = list(all_topos for all_topos,_ in itertools.groupby(all_topos))
print(len(unique))
