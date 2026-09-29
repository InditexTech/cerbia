'use strict';

// Docouture 1.1.1 namespaces SVG ids and #fragment references, but not Mermaid's
// space-separated ARIA IDREFs. Repair only the two known, broken root attributes;
// leave Kroki's SVG markup, graph edges, styles and other references untouched.
function repairDiagramIdrefs(html) {
  return html.replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/g, (svg) => {
    const root = svg.match(/^<svg\b[^>]*>/)?.[0];
    const prefix = root?.match(/\bid="(docouture-diagram-\d+)-container"/)?.[1];
    if (!prefix) return svg;
    const title = `${prefix}-chart-title-container`;
    const desc = `${prefix}-chart-desc-container`;
    if (!svg.includes(`<title id="${title}"`) || !svg.includes(`<desc id="${desc}"`)) return svg;
    const fixedRoot = root
      .replace(/\baria-labelledby="chart-title-container"/, `aria-labelledby="${title}"`)
      .replace(/\baria-describedby="chart-desc-container"/, `aria-describedby="${desc}"`);
    return fixedRoot + svg.slice(root.length);
  });
}

module.exports = { repairDiagramIdrefs };
module.exports.register = function (registry) {
  registry.postprocessor(function () {
    this.process(function (_doc, output) {
      return repairDiagramIdrefs(output);
    });
  });
};
