import anthropic
import json
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert code reviewer. Your job is to review GitHub Pull Request diffs 
and provide clear, actionable, and constructive feedback.

Focus on:
1. Code quality and readability
2. Potential bugs or logic errors
3. Security vulnerabilities
4. Performance concerns
5. Best practices and patterns

Be concise and specific. Reference line numbers or code snippets where relevant.
Avoid nitpicking minor style issues unless a linter/formatter is not configured.

IMPORTANT: Respond ONLY with a valid JSON object in this exact format:
{
  "overall_summary": "2-3 sentence summary of the PR",
  "verdict": "approve" | "request_changes" | "comment",
  "critical_issues": [
    {"description": "issue description", "severity": "high" | "medium" | "low"}
  ],
  "suggestions": [
    {"description": "improvement suggestion"}
  ],
  "positive_notes": ["something done well"]
}"""


class ReviewService:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _build_user_prompt(self, context: dict) -> str:
        diff_preview = context["diff"]

        # Batasi diff agar tidak melebihi token limit
        if len(diff_preview) > 12000:
            diff_preview = diff_preview[:12000] + "\n\n... [diff truncated due to size]"

        return f"""Please review this Pull Request:

**Repository:** {context["repo"]}
**PR #{context["pr_number"]}:** {context["title"]}
**Author:** {context["author"]}
**Branch:** {context["head_branch"]} → {context["base_branch"]}
**Changes:** +{context["additions"]} -{context["deletions"]} across {context["changed_files"]} files

**Description:**
{context["description"]}

**Diff:**
```diff
{diff_preview}
```"""

    def generate_review(self, context: dict) -> dict:
        """Generate AI review dari PR context. Mengembalikan dict hasil review."""
        user_prompt = self._build_user_prompt(context)

        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            raw = message.content[0].text
            review_data = json.loads(raw)
            logger.info(f"Review generated, verdict: {review_data.get('verdict')}")
            return review_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_review()
        except Exception as e:
            logger.error(f"AI review failed: {e}")
            return self._fallback_review()

    def _fallback_review(self) -> dict:
        return {
            "overall_summary": "Review could not be completed due to an error.",
            "verdict": "comment",
            "critical_issues": [],
            "suggestions": [],
            "positive_notes": []
        }

    def format_as_markdown(self, review: dict, pr_context: dict) -> str:
        """Format review dict menjadi Markdown untuk GitHub comment."""
        verdict_emoji = {
            "approve": "✅",
            "request_changes": "🔴",
            "comment": "💬"
        }.get(review.get("verdict", "comment"), "💬")

        verdict_label = {
            "approve": "Approved",
            "request_changes": "Changes Requested",
            "comment": "Review Comment"
        }.get(review.get("verdict", "comment"), "Review Comment")

        lines = [
            f"## {verdict_emoji} AI Code Review — {verdict_label}",
            f"*Reviewed by [PR Review Agent](https://opreklabs.com) · PR #{pr_context['pr_number']}*",
            "",
            "### Summary",
            review.get("overall_summary", ""),
            "",
        ]

        # Critical issues
        critical = review.get("critical_issues", [])
        if critical:
            lines.append("### Issues Found")
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}
            for issue in critical:
                emoji = severity_emoji.get(issue.get("severity", "low"), "🔵")
                lines.append(f"- {emoji} **{issue.get('severity', 'low').capitalize()}:** {issue.get('description', '')}")
            lines.append("")

        # Suggestions
        suggestions = review.get("suggestions", [])
        if suggestions:
            lines.append("### Suggestions")
            for s in suggestions:
                lines.append(f"- 💡 {s.get('description', '')}")
            lines.append("")

        # Positive notes
        positives = review.get("positive_notes", [])
        if positives:
            lines.append("### What's Good")
            for p in positives:
                lines.append(f"- ✨ {p}")
            lines.append("")

        lines.append("---")
        lines.append("*This review was generated automatically by an AI agent. Use your own judgment.*")

        return "\n".join(lines)
