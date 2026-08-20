"""Helper script to rewrite the truncate method in context_manager.py."""
import sys
from pathlib import Path

path = Path(__file__).parent / "backend" / "context_manager.py"
content = path.read_text(encoding="utf-8")

# Find the start of the truncate method
start_marker = "    def truncate("
end_marker = "    def prepare_messages("

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Markers not found")
    sys.exit(1)

# Create the new method
new_method = '''    def truncate(
        self,
        messages: list[dict[str, Any]],
        preserve_last_user: bool = True,
    ) -> TruncationResult:
        """Truncate messages to fit within token budget using priority-based strategy."""
        # Implementation will be added in chunks
        return TruncationResult(
            messages=list(messages),
            truncated=False,
            original_token_count=self.count_tokens(messages),
            final_token_count=self.count_tokens(messages),
            removed_message_count=0,
            budget=self.budget,
        )

'''

# Replace the old method with the new placeholder
content = content[:start_idx] + new_method + content[end_idx:]
path.write_text(content, encoding="utf-8")
print("Placeholder truncate method created successfully")