"""assets/codegraph.html 재생성기 — 코드베이스 AST 콜그래프 (자체 AST, graphify 아님).

모듈 + 최상위 함수/클래스/메서드를 노드로, imports·contains·calls를 엣지로 만든다.
역할별 색으로 클러스터를 구분(app/shared·pages·mcp·evals·tests·rag). graphify CLI가
내는 403노드 헤어볼 대신, 모듈+심볼 단위로 큐레이션한 ~90노드 콜그래프.

사용:  python gen_codegraph.py   →  assets/codegraph.html 갱신 + 노드/엣지 수 출력
"""
import ast
import glob
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "assets", "codegraph.html")
SELF = os.path.basename(__file__)

# 역할 → 색 (Tableau 계열 + 브랜드 periwinkle)
ROLE_COLOR = {
    "core": "#7AA2F7",   # 앱/공유 (jisangfolio·prompts·profile_graph·guardrails·observability·ui·notify·sheetlog)
    "page": "#F28E2B",   # 페이지
    "mcp":  "#B07AA1",   # MCP 서버
    "eval": "#76B7B2",   # 평가 하니스
    "test": "#59A14F",   # 테스트
    "rag":  "#E15759",   # Agentic RAG (오늘 작업 — 눈에 띄게)
}
ROLE_LABEL = {"core": "app / shared", "page": "pages", "mcp": "MCP",
              "eval": "evals", "test": "tests", "rag": "Agentic RAG"}


def collect_files():
    files = []
    for pat in ("*.py", "pages/*.py", "evals/*.py", "tests/*.py"):
        files += glob.glob(os.path.join(ROOT, pat))
    return sorted(f for f in files
                  if "__pycache__" not in f and os.path.basename(f) not in (SELF,))


def module_id(path):
    return os.path.splitext(os.path.basename(path))[0]


def role_of(path):
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    base = module_id(path)
    if rel.startswith("pages/"):
        return "page"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("evals/"):
        return "eval"
    if base == "jisangfolio_mcp":
        return "mcp"
    if base in ("rag_corpus", "agent_rag"):
        return "rag"
    return "core"


def _color(role):
    c = ROLE_COLOR[role]
    return {"background": c, "border": c,
            "highlight": {"background": "#ffffff", "border": c}}


def build():
    files = collect_files()
    modules = {module_id(f): {"path": f, "role": role_of(f)} for f in files}
    mod_ids = set(modules)

    nodes, edges = [], []
    # 이름 → 노드id (calls 해석용). 같은 이름이 여러 모듈에 있으면 첫 정의 우선(best-effort).
    name_to_node = {}
    # 각 모듈이 정의한 (심볼이름 → 노드id)
    defs_by_mod = {}

    for mid, meta in modules.items():
        role = meta["role"]
        try:
            tree = ast.parse(open(meta["path"], encoding="utf-8").read())
        except SyntaxError:
            continue
        # 모듈 노드
        n_defs = 0
        defs_by_mod[mid] = {}
        symbols = []  # (node_id, label, name, body_ast)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nid = f"{mid}__{node.name}"
                symbols.append((nid, f"{node.name}()", node.name, node))
            elif isinstance(node, ast.ClassDef):
                cid = f"{mid}__{node.name}"
                symbols.append((cid, f"{node.name}", node.name, node))
                # 클래스 메서드도 노드로
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("__"):
                        mnid = f"{mid}__{node.name}.{sub.name}"
                        symbols.append((mnid, f"{node.name}.{sub.name}()", sub.name, sub))
                        edges.append({"from": cid, "to": mnid, "title": "contains",
                                      "dashes": False, "width": 1.2, "color": {"opacity": 0.4}})

        for nid, label, name, body in symbols:
            nodes.append({"id": nid, "label": label, "shape": "dot", "size": 9,
                          "color": _color(role),
                          "title": f"{label} — {os.path.basename(meta['path'])} · {ROLE_LABEL[role]}"})
            defs_by_mod[mid][name] = nid
            name_to_node.setdefault(name, nid)
            n_defs += 1

        # contains: 모듈 → 최상위 심볼
        for nid, label, name, body in symbols:
            if "." not in nid.split("__", 1)[1]:  # 최상위만 (메서드는 위에서 class→method로 연결)
                edges.append({"from": mid, "to": nid, "title": "contains",
                              "dashes": False, "width": 1.2, "color": {"opacity": 0.45}})

        modules[mid]["symbols"] = symbols
        modules[mid]["n_defs"] = n_defs

    # 모듈 노드 (크기 = 정의 수 반영)
    for mid, meta in modules.items():
        size = 14 + min(meta.get("n_defs", 0), 12)
        nodes.append({"id": mid, "label": f"{os.path.basename(meta['path'])}",
                      "shape": "dot", "size": size, "color": _color(meta["role"]),
                      "font": {"size": 16, "color": "#e8e8f0"},
                      "title": f"{os.path.relpath(meta['path'], ROOT)} · {ROLE_LABEL[meta['role']]}"})

    # imports: 모듈 → 로컬 모듈
    for mid, meta in modules.items():
        try:
            tree = ast.parse(open(meta["path"], encoding="utf-8").read())
        except SyntaxError:
            continue
        seen = set()
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.ImportFrom) and node.module:
                targets.append(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                targets += [a.name.split(".")[0] for a in node.names]
            for t in targets:
                if t in mod_ids and t != mid and (mid, t) not in seen:
                    seen.add((mid, t))
                    edges.append({"from": mid, "to": t, "title": "imports",
                                  "dashes": True, "width": 2.6, "color": {"opacity": 0.75}})

    # calls: 함수/메서드 → 호출하는 로컬 심볼
    call_seen = set()
    for mid, meta in modules.items():
        for nid, label, name, body in meta.get("symbols", []):
            local = defs_by_mod.get(mid, {})
            for sub in ast.walk(body):
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    called = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
                    if not called:
                        continue
                    target = local.get(called) or name_to_node.get(called)
                    if target and target != nid and (nid, target) not in call_seen:
                        call_seen.add((nid, target))
                        edges.append({"from": nid, "to": target, "title": "calls",
                                      "dashes": False, "width": 1.6,
                                      "arrows": "to", "color": {"opacity": 0.55}})
    return nodes, edges


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>graphify - codebase call graph</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; background: #0f0f1a; }}
  #net {{ width: 100%; height: 100vh; }}
  #legend {{ position: absolute; top: 10px; left: 10px; font: 12px/1.6 -apple-system, sans-serif;
             color: #c8c8d8; background: rgba(26,26,46,.72); padding: 8px 12px; border-radius: 8px; }}
  #legend b {{ color: #e8e8f0; }}
  .sw {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }}
</style>
</head>
<body>
<div id="legend"><b>codebase call graph</b> · {n_nodes} nodes · {n_edges} edges<br>{legend}</div>
<div id="net"></div>
<script>
  var nodes = new vis.DataSet({nodes});
  var edges = new vis.DataSet({edges});
  var network = new vis.Network(document.getElementById("net"), {{nodes: nodes, edges: edges}}, {{
    nodes: {{ borderWidth: 1.5, font: {{ color: "#d8d8e8", size: 12 }} }},
    edges: {{ smooth: {{ type: "continuous" }}, color: {{ color: "#8a8aa0" }} }},
    physics: {{ solver: "forceAtlas2Based",
      forceAtlas2Based: {{ gravitationalConstant: -45, springLength: 90, springConstant: 0.05 }},
      stabilization: {{ iterations: 220 }} }},
    interaction: {{ hover: true, tooltipDelay: 120 }}
  }});
</script>
</body>
</html>
"""


def main():
    nodes, edges = build()
    legend = " &nbsp; ".join(
        f'<span class="sw" style="background:{ROLE_COLOR[r]}"></span>{ROLE_LABEL[r]}'
        for r in ("core", "page", "mcp", "eval", "test", "rag"))
    html = HTML.format(
        nodes=json.dumps(nodes, ensure_ascii=False),
        edges=json.dumps(edges, ensure_ascii=False),
        n_nodes=len(nodes), n_edges=len(edges), legend=legend)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {OUT}")
    print(f"   {len(nodes)} nodes · {len(edges)} edges")
    from collections import Counter
    roles = Counter()
    for m in collect_files():
        roles[role_of(m)] += 1
    print("   모듈:", dict(roles))
    print("   새 파일 포함:", all(any(k in n["id"] for n in nodes) for k in ("rag_corpus", "agent_rag", "4_MLOps_Docs")))


if __name__ == "__main__":
    main()
