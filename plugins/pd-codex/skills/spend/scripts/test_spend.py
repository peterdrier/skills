import json
from pathlib import Path
import tempfile
import unittest

import spend


class SpendResponseTests(unittest.TestCase):
    def parse(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in records))
            return spend.parse_rollout(path)

    def records(self):
        return [
            {"type": "session_meta", "payload": {"id": "root"}},
            {"type": "turn_context", "payload": {
                "turn_id": "task", "model": "gpt-6.1-sol", "effort": "medium"}},
        ]

    def test_many_responses_in_one_task_are_counted_and_priced(self):
        records = self.records()
        records += [{"type": "token_usage_record", "payload": {
            "turn_id": "task", "usage": {"input_tokens": 100, "output_tokens": 10}}}] * 100
        records.append({"type": "event_msg", "payload": {
            "type": "task_complete", "turn_id": "task"}})
        rollout = self.parse(records)
        bucket = next(iter(rollout.buckets.values()))
        self.assertEqual(len(bucket.turns), 1)
        self.assertEqual(bucket.responses, 100)
        self.assertEqual(bucket.usage.total_tokens, 11000)
        self.assertEqual(str(spend.estimate_cost(bucket.model, bucket.usage)), "0.03")
        report = spend.render_report(rollout, [rollout])
        self.assertIn("Task turns", report)
        self.assertIn("Responses: 100", report)

    def test_cumulative_fallback_does_not_invent_response_count(self):
        records = self.records()
        records.append({"type": "event_msg", "payload": {
            "type": "token_count", "info": {"total_token_usage": {"input_tokens": 100}}}})
        rollout = self.parse(records)
        report = spend.render_report(rollout, [rollout])
        self.assertIn("unknown", report)
        self.assertIn("Responses: 0 (recorded only)", report)

    def test_agent_without_usage_renders_waiting_row(self):
        rollout = self.parse([self.records()[0]])
        self.assertIn("waiting", spend.render_report(rollout, [rollout]))


if __name__ == "__main__":
    unittest.main()
