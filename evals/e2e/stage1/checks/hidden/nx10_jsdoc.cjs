// s1-nx-10 hidden check: JSDoc coverage via the TypeScript compiler API of the worktree.
// usage: node nx10_jsdoc.cjs <worktree>   -> prints JSON {ok, problems, components, interfaces}
const fs = require("fs");
const path = require("path");
const wt = path.resolve(process.argv[2]);
const ts = require(require.resolve("typescript", { paths: [wt] }));

const jsDocs = (node) => (node && node.jsDoc ? node.jsDoc.filter((d) => ts.isJSDoc(d)) : []);
const parse = (f) => ts.createSourceFile(f, fs.readFileSync(f, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const problems = [];

function findDecl(sf, name) {
  for (const st of sf.statements) {
    if (ts.isVariableStatement(st)) {
      for (const d of st.declarationList.declarations) if (ts.isIdentifier(d.name) && d.name.text === name) return { decl: d, docNode: st };
    } else if ((ts.isFunctionDeclaration(st) || ts.isClassDeclaration(st)) && st.name && st.name.text === name) {
      return { decl: st, docNode: st };
    }
  }
  return null;
}
function findType(sf, name) {
  for (const st of sf.statements) if ((ts.isTypeAliasDeclaration(st) || ts.isInterfaceDeclaration(st)) && st.name.text === name) return st;
  return null;
}
function unwrapFn(e) {
  while (e && (ts.isParenthesizedExpression(e) || ts.isAsExpression(e))) e = e.expression;
  if (e && ts.isCallExpression(e) && e.arguments.length) return unwrapFn(e.arguments[0]); // memo(...), forwardRef(...)
  return e && (ts.isArrowFunction(e) || ts.isFunctionExpression(e) || ts.isFunctionDeclaration(e)) ? e : null;
}
function members(sf, typeNode, seen = new Set()) {
  if (!typeNode) return [];
  if (ts.isTypeLiteralNode(typeNode)) return typeNode.members;
  if (ts.isIntersectionTypeNode(typeNode)) return typeNode.types.flatMap((t) => members(sf, t, seen));
  if (ts.isTypeReferenceNode(typeNode) && ts.isIdentifier(typeNode.typeName)) {
    const n = typeNode.typeName.text;
    if (seen.has(n)) return [];
    seen.add(n);
    const d = findType(sf, n);
    if (!d) return [];
    return ts.isInterfaceDeclaration(d) ? d.members : members(sf, d.type, seen);
  }
  return [];
}
function propsType(decl, fn) {
  const p = fn && fn.parameters[0];
  if (p && p.type) return p.type;
  // const X: FC<Props> = ...
  if (decl && decl.type && ts.isTypeReferenceNode(decl.type) && decl.type.typeArguments) return decl.type.typeArguments[0];
  return null;
}
const paramNames = (docs) => docs.flatMap((d) => (d.tags || []).filter(ts.isJSDocParameterTag).map((t) => {
  const n = t.name; return ts.isQualifiedName(n) ? n.right.text : n.text;
}));

const components = {};
const cdir = path.join(wt, "components");
for (const f of fs.existsSync(cdir) ? fs.readdirSync(cdir).filter((x) => x.endsWith(".tsx")).sort() : []) {
  const rel = `components/${f}`;
  const sf = parse(path.join(cdir, f));
  const rec = { component: null, jsdoc: false, props: {} };
  components[rel] = rec;
  let decl = null, fn = null, docs = [];
  for (const st of sf.statements) {
    if (ts.isExportAssignment(st) && !st.isExportEquals) {
      docs = docs.concat(jsDocs(st));
      if (ts.isIdentifier(st.expression)) {
        rec.component = st.expression.text;
        const found = findDecl(sf, st.expression.text);
        if (found) { decl = found.decl; docs = docs.concat(jsDocs(found.docNode)); fn = ts.isFunctionDeclaration(decl) ? decl : unwrapFn(decl.initializer); }
      } else { rec.component = "(expression)"; fn = unwrapFn(st.expression); }
    } else if (ts.isFunctionDeclaration(st) && st.modifiers && st.modifiers.some((m) => m.kind === ts.SyntaxKind.DefaultKeyword)) {
      rec.component = st.name ? st.name.text : "(anonymous)"; decl = st; fn = st; docs = docs.concat(jsDocs(st));
    }
  }
  if (!rec.component) { problems.push(`${rel}: no default export found`); continue; }
  rec.jsdoc = docs.length > 0;
  if (!rec.jsdoc) problems.push(`${rel}: component ${rec.component} has no JSDoc block`);
  const params = paramNames(docs);
  for (const m of members(sf, propsType(decl, fn))) {
    const name = m.name && (ts.isIdentifier(m.name) || ts.isStringLiteral(m.name)) ? m.name.text : m.getText(sf);
    const ok = jsDocs(m).length > 0 || params.includes(name);
    rec.props[name] = ok;
    if (!ok) problems.push(`${rel}: prop ${name} has no JSDoc and no matching @param`);
  }
}

const interfaces = {};
const ifile = path.join(wt, "interfaces", "index.ts");
if (fs.existsSync(ifile)) {
  const sf = parse(ifile);
  for (const st of sf.statements) {
    if ((ts.isTypeAliasDeclaration(st) || ts.isInterfaceDeclaration(st) || ts.isEnumDeclaration(st)) &&
        st.modifiers && st.modifiers.some((m) => m.kind === ts.SyntaxKind.ExportKeyword)) {
      interfaces[st.name.text] = jsDocs(st).length > 0;
      if (!interfaces[st.name.text]) problems.push(`interfaces/index.ts: type ${st.name.text} has no JSDoc block`);
    }
  }
  if (!Object.keys(interfaces).length) problems.push("interfaces/index.ts: no exported types");
} else problems.push("interfaces/index.ts missing");
if (!Object.keys(components).length) problems.push("components/*.tsx: none found");

process.stdout.write(JSON.stringify({ ok: problems.length === 0, problems, components, interfaces }, null, 1) + "\n");
