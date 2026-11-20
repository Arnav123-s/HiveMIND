import dataclasses
import unittest
from unittest.mock import patch

from team import signals


class DomainSignalsTests(unittest.TestCase):
    def test_referential_turn_uses_prior_user_only(self):
        question = 'Could you explain that again?'
        history = [('user', 'How does a CPU cache work?'),
                   ('assistant', 'Would you also like to learn Python?')]
        decision = signals.read_request(question, history)
        self.assertEqual(decision['domain'], 'computer_engineering')
        self.assertEqual(decision['signals']['source'], 'context')
        self.assertIsNone(signals.read_request(question))

    def test_senders_independently_observe_their_own_turns(self):
        msg = 'What regularizer can I use when my neural network is overfitting?'
        first = signals.frames(msg, [('user', 'Could you help me debug this program?')])
        second = signals.frames(msg, [('user', 'How does a CPU cache work?')])
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(first[1].payload, second[1].payload)
        self.assertNotEqual(first[2].payload, second[2].payload)
        self.assertIsNone(signals.read_frames(second[0], [first[1], second[2]]))
        self.assertEqual(signals.read_request(msg, [('user', 'Please write a birthday note.')])['domain'],
                         'machine_learning')

    def test_paired_frame_integrity_order_and_retransmission(self):
        task, req, ctx = signals.frames('Debug this Python function that raises a TypeError on empty lists.')
        result = signals.read_frames(task, [req, ctx])
        self.assertEqual(result['domain'], 'coding')
        self.assertEqual(signals.read_frames(task, [ctx, req, ctx]), result)
        foreign = signals.frames('My classifier is overfitting.')[1]
        malformed = [
            [req], [ctx], [req, None], [req, ctx, dataclasses.replace(req, payload=foreign.payload)],
            [dataclasses.replace(req, bundle_id='different paired model'), ctx],
            [dataclasses.replace(req, version=2), ctx], [req, dataclasses.replace(ctx, sender=req.sender)],
            [req, dataclasses.replace(ctx, payload=(16,))], [req, dataclasses.replace(ctx, payload=(63,)*7)]]
        for frames in malformed:
            with self.subTest(frames=frames):
                self.assertIsNone(signals.read_frames(task, frames))

    def test_uncertainty_and_model_unavailability_abstain(self):
        self.assertIsNone(signals.read_request('Do my errands for me.'))
        self.assertIsNone(signals.read_request(''))
        self.assertIsNone(signals.read_request(None))
        with patch.object(signals, '_model', side_effect=ValueError('corrupt pair')):
            self.assertIsNone(signals.read_request('What is a processor cache?'))


if __name__ == '__main__':
    unittest.main()
