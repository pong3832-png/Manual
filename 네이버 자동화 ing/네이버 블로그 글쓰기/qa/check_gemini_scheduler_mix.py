import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "스케줄러.py"


def find_post_types(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "POST_TYPES":
                    return eval_static_list(node.value)
    raise AssertionError("POST_TYPES assignment not found")


def eval_static_list(node):
    if isinstance(node, ast.List):
        return [ast.literal_eval(item) for item in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return eval_static_list(node.left) + eval_static_list(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        left = eval_static_list(node.left)
        right = ast.literal_eval(node.right)
        return left * right
    raise AssertionError(f"unsupported POST_TYPES expression: {ast.dump(node)}")


def main():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)
    post_types = find_post_types(tree)
    assert post_types == ["일상", "일상", "일상"], f"unexpected POST_TYPES: {post_types}"
    assert "schedule_count = len(POST_TYPES)" in source, "schedule_count should come from POST_TYPES"
    assert "random.sample(candidate_minutes, schedule_count)" in source, "time slots should use schedule_count"
    assert "len(candidate_minutes) < schedule_count" in source, "slot shortage check should use schedule_count"
    assert "STALE_TASK_CLEANUP_COUNT = 10" in source, "old 10-task schedule should be cleaned up"
    assert "cleanup_post_tasks()" in source, "post task cleanup should run before registration"
    print("gemini scheduler mix check passed")


if __name__ == "__main__":
    main()
