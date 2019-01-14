import numpy as np
from collections import defaultdict
import re

def get_image_id(filename):
    """
    Get image id for MS COCO images 
    """

    img_id = filename.rsplit('.jpg')[0]
    img_id = img_id.split('_')[2]
    img_id = img_id.lstrip('0')

    return img_id
        

def pad_sentence(sentence, target_length=25, word_to_pad_with='hashemali'):
    """
    Pad input sentences for batch usage in Tensorflow.
    """

    num_words = len(sentence.split())

    while(num_words < target_length):
        sentence = sentence + ' ' + word_to_pad_with
        num_words = len(sentence.split())

    return sentence


def clean_sentence(sentence):
    """
    Remove useless characters and words
    """
    
    sentence = sentence.replace("the", "")
    sentence = sentence.replace("and", "")
    sentence = sentence.replace("/", " ")
    sentence = re.sub(r'[^\w\s]', '', sentence)
    sentence = re.sub(' +', ' ', sentence)
    sentence = sentence.rstrip()

    # Pad the stripped sentence
    sentence = pad_sentence(sentence, target_length=25, word_to_pad_with='hashemali')

    return sentence


def confidence_to_one_hot(confidence):
    """
    Map a confidence value in MS COCO dataset to a one-hot vector suitable for NN Supervision.
    """
    conf_vector = []

    # confidences for (yes) / (maybe, no)
    if confidence == 'yes':
        conf_vector =  [1.0, 0.0, 0.0]

    elif confidence == 'maybe':
        conf_vector = [0.0, 1.0, 0.0]

    else:
        conf_vector =  [0.0, 0.0, 1.0]

    return conf_vector

def load_embedding_from_disks(glove_filename, with_indexes=True):
    """
    Read a GloVe txt file. If `with_indexes=True`, we return a tuple of two dictionnaries
    `(word_to_index_dict, index_to_embedding_array)`, otherwise we return only a direct
    `word_to_embedding_dict` dictionnary mapping from a string to a numpy array.
    """

    print("Loading embedding from disks...")

    if with_indexes:
        word_to_index_dict = dict()
        index_to_embedding_array = []
    else:
        word_to_embedding_dict = dict()

    
    with open(glove_filename, 'r', encoding='utf-8') as glove_file:
        for (i, line) in enumerate(glove_file):
            
            split = line.split(' ')
            
            word = split[0]
            # Save words for further usages
            # with open('vocab_only.txt', 'a', encoding="utf-8") as vocab_file:
            #     vocab_file.write(word+'\n')

            representation = split[1:]
            representation = np.array(
                [float(val) for val in representation]
            )
            if with_indexes:
                word_to_index_dict[word] = i
                index_to_embedding_array.append(representation)
            else:
                word_to_embedding_dict[word] = representation

    _WORD_NOT_FOUND = [0.0]* len(representation)  # Empty representation for unknown words.

    if with_indexes:
        _LAST_INDEX = i + 1
        word_to_index_dict = defaultdict(lambda: _LAST_INDEX, word_to_index_dict)
        index_to_embedding_array = np.array(index_to_embedding_array + [_WORD_NOT_FOUND])
        print("Embedding loaded from disks.")
        return word_to_index_dict, index_to_embedding_array

    else:
        word_to_embedding_dict = defaultdict(lambda: _WORD_NOT_FOUND)
        return word_to_embedding_dict