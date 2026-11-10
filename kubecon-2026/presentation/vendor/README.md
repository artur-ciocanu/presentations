# Local runtime and font provenance

The browser study does not load code, fonts or images from a CDN.

- **Reveal.js 5.1.0**: `reveal/reveal.js`, `reveal/reveal.css`, `reveal/markdown.js`, and `reveal/notes.js`, copied from the npm `reveal.js@5.1.0` package. MIT license in `reveal/LICENSE`. Source: <https://github.com/hakimel/reveal.js/tree/5.1.0>.
- **Inter** (400, 600, 700): copied from the read-only Developer Week slide reference's `vendor/fonts/`. SIL Open Font License 1.1, included in `fonts/Inter-LICENSE.txt`. Source: <https://github.com/rsms/inter>.
- **JetBrains Mono** (400): copied from the same reference. SIL Open Font License 1.1, included in `fonts/JetBrainsMono-OFL.txt`. Source: <https://github.com/JetBrains/JetBrainsMono>.
- **Virgil**: copied from the same reference, used only for brief diagram annotations. SIL Open Font License 1.1, included in `fonts/Virgil-LICENSE.md`, copyright Ellinor Rapp. Source: <https://github.com/excalidraw/virgil>.

The reference projects were not edited. The font binaries are inherited reference assets, not newly downloaded versions. Browser tooling is installed separately in the approved OpenCode temporary directory, not vendored into this presentation.
