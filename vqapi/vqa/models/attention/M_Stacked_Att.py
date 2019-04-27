import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence, pad_sequence
from vqapi.tests import config


class Net(nn.Module):

    def __init__(self, embedding_tokens):
        super(Net, self).__init__()

        # Get number of visual and embedding features
        vision_features = config.output_size * config.output_size * config.output_features
        embedding_features = config.embedding_features

        self.classifier = Classifier(
            in_features=vision_features + config.lstm_hidden_size,
            mid_features=config.mid_features,
            out_features=config.max_answers,
        )

        self.text = TextProcessor(
            embedding_tokens=embedding_tokens,
            embedding_features=config.embedding_features,
            lstm_hidden_size=config.lstm_hidden_size
        )

        self.attention_pass = AttentionMechanism()

        for m in self.modules():
            if isinstance(m, nn.Linear) or isinstance(m, nn.Conv2d):
                init.xavier_uniform(m.weight)
                if m.bias is not None:
                    m.bias.data.zero_()

    def forward(self, v, q, q_lens):

        q = self.text(q, list(q_lens.data))

        # perform attention
        attented_v = self.attention_pass(v, q)

        # Flatten visual features
        attented_v = attented_v.view(attented_v.size(0), -1)

        # Get the mean of question embeddings along axis 1
        q = torch.mean(q, dim=1)

        # Flatten question features
        q = q.view(q.size(0), -1)

        # Normalzie visual features
        attented_v = attented_v / (attented_v.norm(p=2, dim=1, keepdim=True).expand_as(attented_v) + 1e-8)

        # Concatenate visual features and embeddings
        combined = torch.cat([attented_v, q], dim=1)

        # Get the answer predictions
        answer = self.classifier(combined)

        return answer


class Classifier(nn.Sequential):
    def __init__(self, in_features, mid_features, out_features):
        super(Classifier, self).__init__()
        self.add_module('lin1', nn.Linear(in_features, mid_features))
        self.add_module('relu', nn.ReLU())
        self.add_module('lin2', nn.Linear(mid_features, out_features))


class TextProcessor(nn.Module):
    def __init__(self, embedding_tokens, embedding_features, lstm_hidden_size):
        super(TextProcessor, self).__init__()
        self.embedding = nn.Embedding(embedding_tokens, embedding_features, padding_idx=0)
        self.recurrent_layer = nn.LSTM(input_size=embedding_features, hidden_size=lstm_hidden_size, num_layers=1)
        self.tanh = nn.Tanh()
        init.xavier_uniform(self.embedding.weight)

    def forward(self, q, q_lens):
        embedded = self.embedding(q)

        # apply non-linearity
        tanhed = self.tanh(embedded)

        padded = pad_sequence(tanhed, batch_first=True)

        # pack sequence
        packed = pack_padded_sequence(padded, q_lens, batch_first=True)

        # apply rnn
        output, (hn, cn) = self.recurrent_layer(packed)

        # re-pad sequence
        padded = pad_packed_sequence(output, batch_first=True)[0]

        # re-order
        padded = padded.contiguous()

        return padded

class AttentionMechanism(nn.Module):

    def __init__(self):
        super(AttentionMechanism, self).__init__()      # register attention class

        self.l1_v_i = nn.Linear(config.output_features, config.lstm_hidden_size, bias=True)
        self.l1_tanh = nn.Tanh()
        self.l2_v_i = nn.Linear(config.lstm_hidden_size, config.lstm_hidden_size)
        self.l2_v_q = nn.Linear(config.lstm_hidden_size, config.lstm_hidden_size, bias=True)
        self.l2_tanh = nn.Tanh()
        self.l3_h_a = nn.Linear(1, config.lstm_hidden_size, bias=True)
        self.l3_softmax = nn.Softmax(dim=1)

    def forward(v_i, v_q):

        # convert image feature map to image regions feature matrix
        v_i = v_i.view(v_i.size(0), v_i.size(1), -1)

        # apply a linear transformation on v_i to make its rows the same size as q_lens
        v_i = self.l1_tanh(self.l1_v_i(v_i))

        v_i_t = self.l2_v_i(v_i)
        v_q_t = self.l2_v_q(v_q)
        h_a = self.l2_tanh(v_i_t.add(v_q_t[:, None]))
        p_i = self.l3_softmax(h_a)

        # multiply distribution to the image regions features
        v_i_hat = torch.mul(p_i, v_i)

        # v_i_hat is a matrix of size (batch_size, config.lstm_hidden_size, config.output_size^2)
        v_i_hat = torch.sum(v_i_hat, dim=1)


        attented_v = v_i_hat + v_q

        return attended_v






