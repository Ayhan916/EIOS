/**
 * pdfjs-patch-loader.cjs
 *
 * pdfjs-dist v5's pdf.mjs declares `var __webpack_require__ = {}` and
 * `var __webpack_exports__ = {}` at lines 28 and 49. In webpack dev eval mode,
 * these var declarations hoist within the strict-mode eval scope and shadow the
 * outer __webpack_exports__ parameter BEFORE webpack's injected preamble
 * `__webpack_require__.r(__webpack_exports__)` runs — so it receives `undefined`
 * → Object.defineProperty(undefined, ...) → "Properties can only be defined on Objects".
 *
 * Fix: rename the 5 internal pdfjs webpack identifiers so they don't shadow
 * webpack's outer parameters. Also replace `import.meta.url` (used only in a
 * Node.js-only class, never called in browsers) so the eval is valid in Safari.
 */
module.exports = function pdfjsPatchLoader(source) {
  return source
    // Rename pdfjs's own internal webpack runtime object
    .replaceAll("var __webpack_require__ = {};", "var _pdfjsRequire_ = {};")
    .replaceAll("__webpack_require__.d", "_pdfjsRequire_.d")
    .replaceAll("__webpack_require__.o", "_pdfjsRequire_.o")
    // Rename pdfjs's internal exports accumulator (declared but never directly read)
    .replaceAll("var __webpack_exports__ = {};", "var _pdfjsExports_ = {};")
    // Replace import.meta.url — valid ESM-only syntax, only used inside
    // NodeCanvasFactory._createCanvas() which never runs in browsers
    .replaceAll("import.meta.url", '"file://pdfjs-dist"');
};
