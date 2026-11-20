import unittest
from unittest.mock import patch

from team.domain_consensus import read_consensus
from team.signals import read_request


class DomainConsensusTests(unittest.TestCase):
    def test_direct_agreement_preserves_original_advice(self):
        text = 'My code throws a TypeError in this Python function.'
        decision = read_request(text)
        self.assertEqual(decision['domain'], 'coding')
        self.assertIs(read_consensus(text, (), decision), decision)
        self.assertIsNone(read_consensus(text, (), {'domain': 'math'}))

    def test_abstentions_disagreement_and_unavailable_model(self):
        # The learned pair suggested conversation on this unsupported lookup.
        text = 'Please look up the closest pharmacy.'
        self.assertIsNone(read_consensus(text, (), read_request(text)))
        with patch('team.domain_consensus._model', side_effect=OSError('asset unavailable')) as load:
            self.assertIsNone(read_consensus('Compute this derivative.', (), None))
            load.assert_not_called()
            self.assertIsNone(read_consensus('Compute this derivative.', (), {'domain': 'math'}))

    def test_followup_uses_user_context_and_ignores_assistant_words(self):
        message = 'Could you explain that again?'
        history = [('user', 'How does a CPU cache work?'), ('assistant','We can talk about poems too.')]
        decision = read_request(message,history)
        self.assertEqual(decision['domain'], 'computer_engineering')
        self.assertIs(read_consensus(message, history, decision), decision)
        self.assertIsNone(read_consensus(message, (), decision))


if __name__ == '__main__':
    unittest.main()
