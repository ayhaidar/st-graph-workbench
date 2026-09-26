# Third-party notices

Original work in st-graph-workbench is licensed under the Apache License 2.0;
see [LICENSE](LICENSE) and [NOTICE](NOTICE). The third-party code and assets
described below retain their respective licenses and attribution.

It all started with st-link-analysis. st-graph-workbench extends that foundation
with Components v2 integration, graph editing, analysis, incremental commands,
and additional application workflows. Modified and derived code retains the
upstream MIT notice in [licenses/st-link-analysis.txt](licenses/st-link-analysis.txt).

Material Symbols icon assets originate from Google's Material Design Icons
project and are packaged or adapted for this component. Their Apache License 2.0
is included in [licenses/material-symbols.txt](licenses/material-symbols.txt).

The production frontend includes Cytoscape.js, its layout extensions, and their
transitive dependencies. The optional connected-drag controller lazily loads
the MIT-licensed Cytoscape Automove extension. `npm run build` generates
`st_graph_workbench/frontend/build/THIRD_PARTY_LICENSES.txt` from the locked
production packages and their installed license/notice files. This file travels
with both Python distributions, alongside any notices extracted by Webpack.

Python dependencies are installed separately and retain their own licenses.
Documentation-only dependencies are not bundled into the runtime wheel.

Upstream sources:

- [st-link-analysis](https://github.com/AlrasheedA/st-link-analysis)
- [Material Design Icons and Symbols](https://github.com/google/material-design-icons)
- [Cytoscape.js](https://github.com/cytoscape/cytoscape.js)
- [Cytoscape Automove](https://github.com/cytoscape/cytoscape.js-automove)
