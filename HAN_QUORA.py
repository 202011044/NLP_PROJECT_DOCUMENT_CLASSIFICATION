# -*- coding: utf-8 -*-
"""v2_han_nlp_practice_(1) (1).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KpXqZB1fiUfvMUrpODEvsIbeJy4yI8zi
"""

# Commented out IPython magic to ensure Python compatibility.
# %tensorflow_version 1.x

import tensorflow as tf
# print(tensorflow.__version__)
print(tf.__version__)

!pip install pyunpack
!pip install patool
from pyunpack import Archive
# Archive('/content/drive/MyDrive/NLP_PRO/emnlp15.zip').extractall('/content/drive/MyDrive/NLP_PRO/HAN_TEST')
Archive('/content/drive/MyDrive/train.csv.zip').extractall('/content')
Archive('/content/drive/MyDrive/test.csv.zip').extractall('/content')
Archive('/content/drive/MyDrive/sample_submission.csv.zip').extractall('/content')

"""## Prepare data"""

import pandas as pd
import nltk
import itertools
import pickle
import re
# Hyper parameters
WORD_CUT_OFF = 5

def build_vocab(docs, save_path):
  print('Building vocab ...')

  sents = itertools.chain(*[re.split(".",text) for text in docs])
  tokenized_sents = [sent.split() for sent in sents]

  # Count the word frequencies
  word_freq = nltk.FreqDist(itertools.chain(*tokenized_sents))
  print("%d unique words found" % len(word_freq.items()))

  # Cut-off
  retained_words = [w for (w, f) in word_freq.items() if f > WORD_CUT_OFF]
  print("%d words retained" % len(retained_words))

  # Get the most common words and build index_to_word and word_to_index vectors
  # Word index starts from 2, 1 is reserved for UNK, 0 is reserved for padding
  word_to_index = {'PAD': 0, 'UNK': 1}
  for i, w in enumerate(retained_words):
    word_to_index[w] = i + 2
  index_to_word = {i: w for (w, i) in word_to_index.items()}

  print("Vocabulary size = %d" % len(word_to_index))

  with open('{}-w2i.pkl'.format(save_path), 'wb') as f:
    pickle.dump(word_to_index, f)

  with open('{}-i2w.pkl'.format(save_path), 'wb') as f:
    pickle.dump(index_to_word, f)

  return word_to_index




def process_and_save(word_to_index, data, out_file):
  mapped_data = []
  for label, doc in zip(data["target"], data["question_text"]):
    mapped_doc = [[word_to_index.get(word, 1) for word in sent.split()] for sent in re.split("[?.]",doc)]
    mapped_data.append((label, mapped_doc))

  with open(out_file, 'wb') as f:
    pickle.dump(mapped_data, f)


def read_data(data_file, merge_frame_flag):
  
  data = pd.read_csv(data_file)
  if merge_frame_flag == 1:
    submission = pd.read_csv("/content/sample_submission.csv")
    data = data.assign(target=submission["prediction"])
  print('{}, shape={}'.format(data_file, data.shape))
  return data

from google.colab import drive
drive.mount('/content/drive')

"""#Building vocabulary and representing documents using word to index"""

train_data = read_data('/content/train.csv',0)
  #print(train_data["question_text"][1])
  
  word_to_index = build_vocab(train_data['question_text'], '/content/drive/MyDrive/QUORA_CLASSIFICATION')
  
  process_and_save(word_to_index, train_data, '/content/drive/MyDrive/QUORA_CLASSIFICATION/quora-train.pkl')
  
  
  test_data = read_data('/content/test.csv',1)
  process_and_save(word_to_index, test_data, '/content/drive/MyDrive/QUORA_CLASSIFICATION/quora-test.pkl')

""" ## Datareader"""

import pickle
from tqdm import tqdm
import random
import numpy as np

class DataReader:
  def __init__(self, train_file, dev_file, test_file,
               max_word_length=50, max_sent_length=30, num_classes=2):
    self.max_word_length = max_word_length
    self.max_sent_length = max_sent_length
    self.num_classes = num_classes

    self.train_data = self._read_data(train_file)
    self.valid_data = self._read_data(dev_file)
    self.test_data = self._read_data(test_file)
  def _read_data(self, file_path):
    print('Reading data from %s' % file_path)
    new_data = []
    with open(file_path, 'rb') as f:
      data = pickle.load(f)
      random.shuffle(data)
      for label, doc in data:
        doc = doc[:self.max_sent_length]
        doc = [sent[:self.max_word_length] for sent in doc]

        assert label >= 0 and label < self.num_classes

        new_data.append((doc, label))

    new_data = sorted(new_data, key=lambda x: len(x[0]))
    return new_data

  def _batch_iterator(self, data, batch_size, desc=None):
    num_batches = int(np.ceil(len(data) / batch_size))
    for b in tqdm(range(num_batches), desc):
      begin_offset = batch_size * b
      end_offset = batch_size * b + batch_size
      if end_offset > len(data):
        end_offset = len(data)

      doc_batch = []
      label_batch = []
      for offset in range(begin_offset, end_offset):
        doc_batch.append(data[offset][0])
        label_batch.append(data[offset][1])

      yield doc_batch, label_batch

  def read_train_set(self, batch_size, shuffle=False):
    if shuffle:
      random.shuffle(self.train_data)
    return self._batch_iterator(self.train_data, batch_size, desc='Training')

  def read_valid_set(self, batch_size):
    return self._batch_iterator(self.valid_data, batch_size, desc='Validating')

  def read_test_set(self, batch_size):
    return self._batch_iterator(self.test_data, batch_size, desc='Testing')

"""## Utils"""

# import tensorflow.compat.v1 as tf
import numpy as np
import pickle


def get_shape(tensor):
  static_shape = tensor.shape.as_list()
  dynamic_shape = tf.unstack(tf.shape(tensor))
  dims = [s[1] if s[0] is None else s[0]
          for s in zip(static_shape, dynamic_shape)]
  return dims



def read_vocab(vocab_file):
  print('Loading vocabulary ...')
  with open(vocab_file, 'rb') as f:
    word_to_index = pickle.load(f)
    print('Vocabulary size = %d' % len(word_to_index))
    return word_to_index


def batch_doc_normalize(docs):
  sent_lengths = np.array([len(doc) for doc in docs], dtype=np.int32)
  max_sent_length = sent_lengths.max()
  word_lengths = [[len(sent) for sent in doc] for doc in docs]
  max_word_length = max(map(max, word_lengths))

  padded_docs = np.zeros(shape=[len(docs), max_sent_length, max_word_length], dtype=np.int32)  # PADDING 0
  word_lengths = np.zeros(shape=[len(docs), max_sent_length], dtype=np.int32)
  for i, doc in enumerate(docs):
    for j, sent in enumerate(doc):
      word_lengths[i, j] = len(sent)
      for k, word in enumerate(sent):
        padded_docs[i, j, k] = word

  return padded_docs, sent_lengths, max_sent_length, word_lengths, max_word_length


def load_glove(glove_file, emb_size, vocab):
  print('Loading Glove pre-trained word embeddings ...')
  embedding_weights = {}
  f = open(glove_file, encoding='utf-8')
  for line in f:
    values = line.split()
    word = values[0]
    vector = np.asarray(values[1:], dtype='float32')
    embedding_weights[word] = vector
  f.close()
  print('Total {} word vectors in {}'.format(len(embedding_weights), glove_file))

  embedding_matrix = np.random.uniform(-0.5, 0.5, (len(vocab), emb_size)) / emb_size

  oov_count = 0
  for word, i in vocab.items():
    embedding_vector = embedding_weights.get(word)
    if embedding_vector is not None:
      embedding_matrix[i] = embedding_vector
    else:
      oov_count += 1
  print('Number of OOV words = %d' % oov_count)

  return embedding_matrix

"""## Layers"""

# # import tensorflow.compat.v1 as tf
# import numpy as np

# try:
#   from tensorflow.contrib.rnn import LSTMStateTuple
# except ImportError:
#   LSTMStateTuple = tf.nn.rnn_cell.LSTMStateTuple



# def bidirectional_rnn(cell_fw, cell_bw, inputs, input_lengths,
#                       initial_state_fw=None, initial_state_bw=None,
#                       scope=None):
#   with tf.compat.v1.variable_scope(scope or 'bi_rnn',reuse=tf.compat.v1.AUTO_REUSE ) as scope:
#     (fw_outputs, bw_outputs), (fw_state, bw_state) = tf.compat.v1.nn.bidirectional_dynamic_rnn(
#       cell_fw=cell_fw,
#       cell_bw=cell_bw,
#       inputs=inputs,
#       sequence_length=input_lengths,
#       initial_state_fw=initial_state_fw,
#       initial_state_bw=initial_state_bw,
#       dtype=tf.float32,
#       scope=scope
#     )
#     outputs = tf.compat.v1.concat((fw_outputs, bw_outputs), axis=2)

#     def concatenate_state(fw_state, bw_state):
#       if isinstance(fw_state, LSTMStateTuple):
#         state_c = tf.concat(
#           (fw_state.c, bw_state.c), 1, name='bidirectional_concat_c')
#         state_h = tf.concat(
#           (fw_state.h, bw_state.h), 1, name='bidirectional_concat_h')
#         state = LSTMStateTuple(c=state_c, h=state_h)
#         return state
#       elif isinstance(fw_state, tf.Tensor):
#         state = tf.compat.v1.concat((fw_state, bw_state), 1,
#                           name='bidirectional_concat')
#         return state
#       elif (isinstance(fw_state, tuple) and
#             isinstance(bw_state, tuple) and
#             len(fw_state) == len(bw_state)):
#         # multilayer
#         state = tuple(concatenate_state(fw, bw)
#                       for fw, bw in zip(fw_state, bw_state))
#         return state

#       else:
#         raise ValueError(
#           'unknown state type: {}'.format((fw_state, bw_state)))

#     state = concatenate_state(fw_state, bw_state)
#     return outputs, state


# def masking(scores, sequence_lengths, score_mask_value=tf.compat.v1.constant(-np.inf)):
#   score_mask = tf.compat.v1.sequence_mask(sequence_lengths, maxlen=tf.compat.v1.shape(scores)[1])
#   score_mask_values = score_mask_value * tf.compat.v1.ones_like(scores)
#   return tf.compat.v1.where(score_mask, scores, score_mask_values)


# def attention(inputs, att_dim, sequence_lengths, scope=None):
#   #assert len(inputs.get_shape()) == 3 and inputs.get_shape()[-1].value is not None

#   with tf.compat.v1.variable_scope(scope or 'attention',reuse=tf.compat.v1.AUTO_REUSE):
#     word_att_W = tf.compat.v1.get_variable(name='att_W', shape=[att_dim, 1],synchronization=tf.VariableSynchronization.AUTO)

#     projection = tf.compat.v1.layers.dense(inputs, att_dim, tf.nn.tanh, name='projection')

#     alpha = tf.compat.v1.matmul(tf.compat.v1.reshape(projection, shape=[-1, att_dim]), word_att_W)
#     alpha = tf.compat.v1.reshape(alpha, shape=[-1, get_shape(inputs)[1]])
#     alpha = masking(alpha, sequence_lengths, tf.compat.v1.constant(-1e15, dtype=tf.compat.v1.float32))
#     alpha = tf.compat.v1.nn.softmax(alpha)

#     outputs = tf.compat.v1.reduce_sum(inputs * tf.compat.v1.expand_dims(alpha, 2), axis=1)
#     return outputs, alpha


import numpy as np

try:
  from tensorflow.contrib.rnn import LSTMStateTuple
except ImportError:
  LSTMStateTuple = tf.nn.rnn_cell.LSTMStateTuple



def bidirectional_rnn(cell_fw, cell_bw, inputs, input_lengths,
                      initial_state_fw=None, initial_state_bw=None,
                      scope=None):
  with tf.variable_scope(scope or 'bi_rnn') as scope:
    (fw_outputs, bw_outputs), (fw_state, bw_state) = tf.nn.bidirectional_dynamic_rnn(
      cell_fw=cell_fw,
      cell_bw=cell_bw,
      inputs=inputs,
      sequence_length=input_lengths,
      initial_state_fw=initial_state_fw,
      initial_state_bw=initial_state_bw,
      dtype=tf.float32,
      scope=scope
    )
    outputs = tf.concat((fw_outputs, bw_outputs), axis=2)

    def concatenate_state(fw_state, bw_state):
      if isinstance(fw_state, LSTMStateTuple):
        state_c = tf.concat(
          (fw_state.c, bw_state.c), 1, name='bidirectional_concat_c')
        state_h = tf.concat(
          (fw_state.h, bw_state.h), 1, name='bidirectional_concat_h')
        state = LSTMStateTuple(c=state_c, h=state_h)
        return state
      elif isinstance(fw_state, tf.Tensor):
        state = tf.concat((fw_state, bw_state), 1,
                          name='bidirectional_concat')
        return state
      elif (isinstance(fw_state, tuple) and
            isinstance(bw_state, tuple) and
            len(fw_state) == len(bw_state)):
        # multilayer
        state = tuple(concatenate_state(fw, bw)
                      for fw, bw in zip(fw_state, bw_state))
        return state

      else:
        raise ValueError(
          'unknown state type: {}'.format((fw_state, bw_state)))

    state = concatenate_state(fw_state, bw_state)
    return outputs, state


def masking(scores, sequence_lengths, score_mask_value=tf.constant(-np.inf)):
  score_mask = tf.sequence_mask(sequence_lengths, maxlen=tf.shape(scores)[1])
  score_mask_values = score_mask_value * tf.ones_like(scores)
  return tf.where(score_mask, scores, score_mask_values)


def attention(inputs, att_dim, sequence_lengths, scope=None):
  assert len(inputs.get_shape()) == 3 and inputs.get_shape()[-1].value is not None

  with tf.variable_scope(scope or 'attention'):
    word_att_W = tf.get_variable(name='att_W', shape=[att_dim, 1])

    projection = tf.layers.dense(inputs, att_dim, tf.nn.tanh, name='projection')

    alpha = tf.matmul(tf.reshape(projection, shape=[-1, att_dim]), word_att_W)
    alpha = tf.reshape(alpha, shape=[-1, get_shape(inputs)[1]])
    alpha = masking(alpha, sequence_lengths, tf.constant(-1e15, dtype=tf.float32))
    alpha = tf.nn.softmax(alpha)

    outputs = tf.reduce_sum(inputs * tf.expand_dims(alpha, 2), axis=1)
    return outputs, alpha

"""## Model"""

# # import tensorflow as tf
# from tensorflow.keras import layers
# #from layers import bidirectional_rnn, attention
# #from utils import get_shape, batch_doc_normalize


# class Model:
  
#   def __init__(self, cell_dim, att_dim, vocab_size, emb_size, num_classes, dropout_rate, pretrained_embs):
#     self.cell_dim = cell_dim
#     self.att_dim = att_dim
#     self.emb_size = emb_size
#     self.vocab_size = vocab_size
#     self.num_classes = num_classes
#     self.dropout_rate = dropout_rate
#     self.pretrained_embs = pretrained_embs

#     self.docs = tf.compat.v1.placeholder(shape=(None, None, None), dtype=tf.int32, name='docs')
#     self.sent_lengths = tf.compat.v1.placeholder(shape=(None,), dtype=tf.int32, name='sent_lengths')
#     self.word_lengths = tf.compat.v1.placeholder(shape=(None, None), dtype=tf.int32, name='word_lengths')
#     self.max_word_length = tf.compat.v1.placeholder(dtype=tf.int32, name='max_word_length')
#     self.max_sent_length = tf.compat.v1.placeholder(dtype=tf.int32, name='max_sent_length')
#     self.labels = tf.compat.v1.placeholder(shape=(None), dtype=tf.int32, name='labels')
#     self.is_training = tf.compat.v1.placeholder(dtype=tf.bool, name='is_training')

#     self._init_embedding()
#     self._init_word_encoder()
#     self._init_sent_encoder()
#     self._init_classifier()

  
  
#   def _init_embedding(self):
#     with tf.compat.v1.variable_scope('embedding',reuse = True):
#       self.embedding_matrix = tf.compat.v1.get_variable(name='embedding_matrix',
#                                               shape=[self.vocab_size, self.emb_size],
#                                               initializer=tf.compat.v1.constant_initializer(self.pretrained_embs),
#                                               dtype=tf.float32,synchronization=tf.VariableSynchronization.AUTO)
#       self.embedded_inputs = tf.compat.v1.nn.embedding_lookup(self.embedding_matrix, self.docs)
  
  
  
#   def _init_word_encoder(self):
#     with tf.compat.v1.variable_scope('word-encoder',reuse=tf.compat.v1.AUTO_REUSE) as scope:
#       word_inputs = tf.compat.v1.reshape(self.embedded_inputs, [-1, self.max_word_length, self.emb_size])
#       word_lengths = tf.compat.v1.reshape(self.word_lengths, [-1])

#       # word encoder
#       cell_fw = layers.GRUCell(self.cell_dim, name='cell_fw')
#       cell_bw = layers.GRUCell(self.cell_dim, name='cell_bw')

#       init_state_fw = tf.compat.v1.tile(tf.compat.v1.get_variable('init_state_fw',
#                                               shape=[1, self.cell_dim],
#                                               initializer=tf.compat.v1.constant_initializer(0)),
#                               multiples=[get_shape(word_inputs)[0], 1])
#       init_state_bw = tf.compat.v1.tile(tf.compat.v1.get_variable('init_state_bw',
#                                               shape=[1, self.cell_dim],
#                                               initializer=tf.compat.v1.constant_initializer(0)),
#                               multiples=[get_shape(word_inputs)[0], 1])

#       rnn_outputs, _ = bidirectional_rnn(cell_fw=cell_fw,
#                                          cell_bw=cell_bw,
#                                          inputs=word_inputs,
#                                          input_lengths=word_lengths,
#                                          initial_state_fw=init_state_fw,
#                                          initial_state_bw=init_state_bw,
#                                          scope=scope)

#       word_outputs, word_att_weights = attention(inputs=rnn_outputs,
#                                                  att_dim=self.att_dim,
#                                                  sequence_lengths=word_lengths)
#       self.word_outputs = tf.compat.v1.layers.dropout(word_outputs, self.dropout_rate, training=self.is_training)

#   def _init_sent_encoder(self):
#     with tf.compat.v1.variable_scope('sent-encoder',reuse=tf.compat.v1.AUTO_REUSE) as scope:
#       sent_inputs = tf.compat.v1.reshape(self.word_outputs, [-1, self.max_sent_length, 2 * self.cell_dim])

#       # sentence encoder
#       cell_fw = layers.GRUCell(self.cell_dim, name='cell_fw')
#       cell_bw = layers.GRUCell(self.cell_dim, name='cell_bw')

#       init_state_fw = tf.compat.v1.tile(tf.compat.v1.get_variable('init_state_fw',
#                                               shape=[1, self.cell_dim],
#                                               initializer=tf.compat.v1.constant_initializer(0)),
#                               multiples=[get_shape(sent_inputs)[0], 1])
#       init_state_bw = tf.compat.v1.tile(tf.compat.v1.get_variable('init_state_bw',
#                                               shape=[1, self.cell_dim],
#                                               initializer=tf.compat.v1.constant_initializer(0)),
#                               multiples=[get_shape(sent_inputs)[0], 1])

#       rnn_outputs, _ = bidirectional_rnn(cell_fw=cell_fw,
#                                          cell_bw=cell_bw,
#                                          inputs=sent_inputs,
#                                          input_lengths=self.sent_lengths,
#                                          initial_state_fw=init_state_fw,
#                                          initial_state_bw=init_state_bw,
#                                          scope=scope)

#       sent_outputs, sent_att_weights = attention(inputs=rnn_outputs,
#                                                  att_dim=self.att_dim,
#                                                  sequence_lengths=self.sent_lengths)
#       self.sent_outputs = tf.compat.v1.layers.dropout(sent_outputs, self.dropout_rate, training=self.is_training)

#   def _init_classifier(self):
#     with tf.compat.v1.variable_scope('classifier',reuse=tf.compat.v1.AUTO_REUSE):
#       self.logits = tf.compat.v1.layers.dense(inputs=self.sent_outputs, units=self.num_classes, name='logits')

#   def get_feed_dict(self, docs, labels, training=False):
#     padded_docs, sent_lengths, max_sent_length, word_lengths, max_word_length = batch_doc_normalize(docs)
#     fd = {
#       self.docs: padded_docs,
#       self.sent_lengths: sent_lengths,
#       self.word_lengths: word_lengths,
#       self.max_sent_length: max_sent_length,
#       self.max_word_length: max_word_length,
#       self.labels: labels,
#       self.is_training: training
#     }
#     return fd


import tensorflow.contrib.rnn as rnn
# from layers import bidirectional_rnn, attention


class Model:
  def __init__(self, cell_dim, att_dim, vocab_size, emb_size, num_classes, dropout_rate, pretrained_embs):
    self.cell_dim = cell_dim
    self.att_dim = att_dim
    self.emb_size = emb_size
    self.vocab_size = vocab_size
    self.num_classes = num_classes
    self.dropout_rate = dropout_rate
    self.pretrained_embs = pretrained_embs

    self.docs = tf.placeholder(shape=(None, None, None), dtype=tf.int32, name='docs')
    self.sent_lengths = tf.placeholder(shape=(None,), dtype=tf.int32, name='sent_lengths')
    self.word_lengths = tf.placeholder(shape=(None, None), dtype=tf.int32, name='word_lengths')
    self.max_word_length = tf.placeholder(dtype=tf.int32, name='max_word_length')
    self.max_sent_length = tf.placeholder(dtype=tf.int32, name='max_sent_length')
    self.labels = tf.placeholder(shape=(None), dtype=tf.int32, name='labels')
    self.is_training = tf.placeholder(dtype=tf.bool, name='is_training')

    self._init_embedding()
    self._init_word_encoder()
    self._init_sent_encoder()
    self._init_classifier()

  def _init_embedding(self):
    with tf.variable_scope('embedding'):
      self.embedding_matrix = tf.get_variable(name='embedding_matrix',
                                              shape=[self.vocab_size, self.emb_size],
                                              initializer=tf.constant_initializer(self.pretrained_embs),
                                              dtype=tf.float32)
      self.embedded_inputs = tf.nn.embedding_lookup(self.embedding_matrix, self.docs)

  def _init_word_encoder(self):
    with tf.variable_scope('word-encoder') as scope:
      word_inputs = tf.reshape(self.embedded_inputs, [-1, self.max_word_length, self.emb_size])
      word_lengths = tf.reshape(self.word_lengths, [-1])

      # word encoder
      cell_fw = rnn.GRUCell(self.cell_dim, name='cell_fw')
      cell_bw = rnn.GRUCell(self.cell_dim, name='cell_bw')

      init_state_fw = tf.tile(tf.get_variable('init_state_fw',
                                              shape=[1, self.cell_dim],
                                              initializer=tf.constant_initializer(0)),
                              multiples=[get_shape(word_inputs)[0], 1])
      init_state_bw = tf.tile(tf.get_variable('init_state_bw',
                                              shape=[1, self.cell_dim],
                                              initializer=tf.constant_initializer(0)),
                              multiples=[get_shape(word_inputs)[0], 1])

      rnn_outputs, _ = bidirectional_rnn(cell_fw=cell_fw,
                                         cell_bw=cell_bw,
                                         inputs=word_inputs,
                                         input_lengths=word_lengths,
                                         initial_state_fw=init_state_fw,
                                         initial_state_bw=init_state_bw,
                                         scope=scope)

      word_outputs, word_att_weights = attention(inputs=rnn_outputs,
                                                 att_dim=self.att_dim,
                                                 sequence_lengths=word_lengths)
      self.word_outputs = tf.layers.dropout(word_outputs, self.dropout_rate, training=self.is_training)

  def _init_sent_encoder(self):
    with tf.variable_scope('sent-encoder') as scope:
      sent_inputs = tf.reshape(self.word_outputs, [-1, self.max_sent_length, 2 * self.cell_dim])

      # sentence encoder
      cell_fw = rnn.GRUCell(self.cell_dim, name='cell_fw')
      cell_bw = rnn.GRUCell(self.cell_dim, name='cell_bw')

      init_state_fw = tf.tile(tf.get_variable('init_state_fw',
                                              shape=[1, self.cell_dim],
                                              initializer=tf.constant_initializer(0)),
                              multiples=[get_shape(sent_inputs)[0], 1])
      init_state_bw = tf.tile(tf.get_variable('init_state_bw',
                                              shape=[1, self.cell_dim],
                                              initializer=tf.constant_initializer(0)),
                              multiples=[get_shape(sent_inputs)[0], 1])

      rnn_outputs, _ = bidirectional_rnn(cell_fw=cell_fw,
                                         cell_bw=cell_bw,
                                         inputs=sent_inputs,
                                         input_lengths=self.sent_lengths,
                                         initial_state_fw=init_state_fw,
                                         initial_state_bw=init_state_bw,
                                         scope=scope)

      sent_outputs, sent_att_weights = attention(inputs=rnn_outputs,
                                                 att_dim=self.att_dim,
                                                 sequence_lengths=self.sent_lengths)
      self.sent_outputs = tf.layers.dropout(sent_outputs, self.dropout_rate, training=self.is_training)

  def _init_classifier(self):
    with tf.variable_scope('classifier'):
      self.logits = tf.layers.dense(inputs=self.sent_outputs, units=self.num_classes, name='logits')

  def get_feed_dict(self, docs, labels, training=False):
    padded_docs, sent_lengths, max_sent_length, word_lengths, max_word_length = batch_doc_normalize(docs)
    fd = {
      self.docs: padded_docs,
      self.sent_lengths: sent_lengths,
      self.word_lengths: word_lengths,
      self.max_sent_length: max_sent_length,
      self.max_word_length: max_word_length,
      self.labels: labels,
      self.is_training: training
    }
    return fd

"""## Train"""

# import tensorflow.compat.v1 as tf
from datetime import datetime

# Parameters
# ==================================================
#FLAGS = tf.flags.FLAGS

#tf.flags.DEFINE_string("checkpoint_dir", '/content/drive/MyDrive/NLP_PRO/QUORA_CLASSIFICATION',
#                       """Path to checkpoint folder""")
#tf.flags.DEFINE_string("log_dir", '/content/drive/MyDrive/NLP_PRO/QUORA_CLASSIFICATION',
#                       """Path to log folder""")






cell_dim = 50
att_dim = 100 
emb_size = 200 
num_classes = 2
num_epochs = 2
batch_size = 64
display_step = 20
learning_rate = 0.0005 
max_grad_norm = 5.0 
dropout_rate = 0.5
allow_soft_placement = True

'''

tf.flags.DEFINE_integer("cell_dim", 50,
                        """Hidden dimensions of GRU cells (default: 50)""")
tf.flags.DEFINE_integer("att_dim", 100,
                        """Dimensionality of attention spaces (default: 100)""")
tf.flags.DEFINE_integer("emb_size", 200,
                        """Dimensionality of word embedding (default: 200)""")
tf.flags.DEFINE_integer("num_classes", 2,
                        """Number of classes (default: 2)""")

#tf.flags.DEFINE_integer("num_checkpoints", 1,
#                        """Number of checkpoints to store (default: 1)""")
tf.flags.DEFINE_integer("num_epochs", 20,
                        """Number of training epochs (default: 20)""")
tf.flags.DEFINE_integer("batch_size", 64,
                        """Batch size (default: 64)""")
tf.flags.DEFINE_integer("display_step", 20,
                        """Number of steps to display log into TensorBoard (default: 20)""")

tf.flags.DEFINE_float("learning_rate", 0.0005,
                      """Learning rate (default: 0.0005)""")
tf.flags.DEFINE_float("max_grad_norm", 5.0,
                      """Maximum value of the global norm of the gradients for clipping (default: 5.0)""")
tf.flags.DEFINE_float("dropout_rate", 0.5,
                      """Probability of dropping neurons (default: 0.5)""")

tf.flags.DEFINE_boolean("allow_soft_placement", True,
                        """Allow device soft device placement""")
'''
#if not tf.gfile.Exists(FLAGS.checkpoint_dir):
#  tf.gfile.MakeDirs(FLAGS.checkpoint_dir)

#if not tf.gfile.Exists(FLAGS.log_dir):
#  tf.gfile.MakeDirs(FLAGS.log_dir)

#train_writer = tf.summary.FileWriter(FLAGS.log_dir + '/train')
#valid_writer = tf.summary.FileWriter(FLAGS.log_dir + '/valid')
#test_writer = tf.summary.FileWriter(FLAGS.log_dir + '/test')


def loss_fn(labels, logits):
  onehot_labels = tf.compat.v1.one_hot(labels, depth=num_classes)
  cross_entropy_loss = tf.compat.v1.losses.softmax_cross_entropy(onehot_labels=onehot_labels,
                                                       logits=logits)
  #tf.summary.scalar('loss', cross_entropy_loss)
  return cross_entropy_loss


def train_fn(loss):
    print(1) 
    trained_vars = tf.compat.v1.trainable_variables()
    print(2)
    #count_parameters(trained_vars)
    print(3)
    # Gradient clipping
    gradients = tf.compat.v1.gradients(loss, trained_vars)
    print(4)
    clipped_grads, global_norm =tf.compat.v1.clip_by_global_norm(gradients, max_grad_norm)
    #tf.summary.scalar('global_grad_norm', global_norm)

    # Add gradients and vars to summary
    # for gradient, var in list(zip(clipped_grads, trained_vars)):
    #   if 'attention' in var.name:
    #     tf.summary.histogram(var.name + '/gradient', gradient)
    #     tf.summary.histogram(var.name, var)

    # Define optimizer
    print(5)
    global_step = tf.compat.v1.train.get_or_create_global_step()
    print(6)
    optimizer = tf.compat.v1.train.RMSPropOptimizer(learning_rate)
    print(7)
    train_op = optimizer.apply_gradients(zip(clipped_grads, trained_vars),
                                       name='train_op',
                                       global_step=global_step)
    return train_op, global_step


def eval_fn(labels, logits):
  predictions = tf.compat.v1.argmax(logits, axis=-1)
  correct_preds = tf.compat.v1.equal(predictions, tf.compat.v1.cast(labels, tf.int64))
  batch_acc = tf.compat.v1.reduce_mean(tf.compat.v1.cast(correct_preds, tf.compat.v1.float32))
  #tf.summary.scalar('accuracy', batch_acc)

  total_acc, acc_update = tf.compat.v1.metrics.accuracy(labels, predictions, name='metrics/acc')
  metrics_vars = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.LOCAL_VARIABLES, scope="metrics")
  metrics_init = tf.compat.v1.variables_initializer(var_list=metrics_vars)

  return batch_acc, total_acc, acc_update, metrics_init

"""#Loading pretrained glove"""

import urllib.request
# urllib.request.urlretrieve('https://nlp.stanford.edu/data/glove.6B.zip','/content/drive/MyDrive/QUORA_CLASSIFICATION/glove.6B.zip')

# !unzip "/content/drive/MyDrive/QUORA_CLASSIFICATION/glove.6B.zip" -d "/content/drive/MyDrive/QUORA_CLASSIFICATION/glove_embedding/"

vocab = read_vocab('/content/drive/MyDrive/QUORA_CLASSIFICATION-w2i.pkl')
  glove_embs = load_glove('/content/drive/MyDrive/QUORA_CLASSIFICATION/glove_embedding/glove.6B.{}d.txt'.format(emb_size), emb_size, vocab)
  !cp /content/drive/MyDrive/QUORA_CLASSIFICATION/quora-train.pkl /content/
  !cp /content/drive/MyDrive/QUORA_CLASSIFICATION/quora-test.pkl /content/ 
  data_reader = DataReader(train_file='/content/quora-train.pkl',
                           dev_file='/content/quora-test.pkl',
                           test_file='/content/quora-test.pkl')

  
 
 
  tf.compat.v1.reset_default_graph()   
  config = tf.compat.v1.ConfigProto(allow_soft_placement=allow_soft_placement)
  with tf.compat.v1.Session(config=config) as sess:
    model = Model(cell_dim=cell_dim,
                  att_dim=att_dim,
                  vocab_size=len(vocab),
                  emb_size=emb_size,
                  num_classes=num_classes,
                  dropout_rate=dropout_rate,
                  pretrained_embs=glove_embs)

    loss = loss_fn(model.labels, model.logits)
    train_op, global_step = train_fn(loss)
    batch_acc, total_acc, acc_update, metrics_init = eval_fn(model.labels, model.logits)
    #summary_op = tf.summary.merge_all()
    sess.run(tf.global_variables_initializer())

    #train_writer.add_graph(sess.graph)
    #saver = tf.train.Saver(max_to_keep=FLAGS.num_checkpoints)

    print('\n{}> Start training'.format(datetime.now()))

    epoch = 0
    valid_step = 0
    test_step = 0
    train_test_prop = len(data_reader.train_data) / len(data_reader.test_data)
    test_batch_size = int(batch_size / train_test_prop)
    best_acc = float('-inf')

    while epoch < num_epochs:
      epoch += 1
      print('\n{}> Epoch: {}'.format(datetime.now(), epoch))

      sess.run(metrics_init)
      for batch_docs, batch_labels in data_reader.read_train_set(batch_size, shuffle=True):
        _step, _, _loss, _acc, _ = sess.run(fetches = [global_step, train_op, loss, batch_acc, acc_update],
                                         feed_dict=model.get_feed_dict(batch_docs, batch_labels, training=True))
        if _step % display_step == 0:
          _summary = sess.run(fetches = [] ,feed_dict=model.get_feed_dict(batch_docs, batch_labels))
          print("train summary")
          print(_summary)
          #train_writer.add_summary(_summary, global_step=_step)
      print('Training accuracy = {:.2f}'.format(sess.run(total_acc) * 100))

      sess.run(metrics_init)
      for batch_docs, batch_labels in data_reader.read_valid_set(test_batch_size):
        _loss, _acc, _  = sess.run(fetches= [loss, batch_acc, acc_update], feed_dict=model.get_feed_dict(batch_docs, batch_labels))
        valid_step += 1
        if valid_step % display_step == 0:
          _summary = sess.run(fetches = [],feed_dict=model.get_feed_dict(batch_docs, batch_labels))
          print("val_summary")
          print(_summary)
          #valid_writer.add_summary(_summary, global_step=valid_step)
      print('Validation accuracy = {:.2f}'.format(sess.run(total_acc) * 100))

      
 


 # write something here ########