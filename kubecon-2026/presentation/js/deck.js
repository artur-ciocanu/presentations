async function startDeck() {
  const staticReview = new URLSearchParams(location.search).has('static');
  let assetError;
  const assets = {
    id: 'deck-assets',
    async init(deck) {
      try {
        const sections = Array.from(deck.getRevealElement().querySelectorAll('.slides > section'));
        sections.forEach((section, index) => {
          if (section.classList.contains('title')) return;
          const footer = document.createElement('div');
          footer.className = 'footer';
          const left = document.createElement('span');
          left.textContent = 'Artur Ciocanu · KubeCon 2026';
          const right = document.createElement('span');
          right.textContent = String(index + 1).padStart(2, '0');
          footer.append(left, right);
          section.append(footer);
        });
        await Promise.all(Array.from(document.querySelectorAll('[data-svg]')).map(async holder => {
          const response = await fetch(holder.dataset.svg);
          if (!response.ok) throw new Error(`Unable to load ${holder.dataset.svg}: ${response.status}`);
          const xml = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
          if (xml.querySelector('parsererror')) throw new Error(`Invalid SVG: ${holder.dataset.svg}`);
          holder.replaceChildren(document.importNode(xml.documentElement, true));
        }));
        await document.fonts.ready;
      } catch (error) { assetError = error; }
    }
  };
  await Reveal.initialize({
    width: 1600, height: 900, margin: 0, center: false,
    hash: true, hashOneBasedIndex: false,
    controls: false, controlsTutorial: false, progress: true,
    fragments: !staticReview, slideNumber: false,
    transition: 'none', backgroundTransition: 'none', navigationMode: 'linear',
    plugins: [RevealMarkdown, assets, RevealNotes]
  });
  if (assetError) throw assetError;
  await document.fonts.ready;
  window.deckReady = true;
}
startDeck().catch(error => {
  console.error(error);
  const alert = document.getElementById('load-error');
  alert.textContent = `${error.message}. Serve the presentation directory over HTTP (python3 -m http.server).`;
  alert.hidden = false;
});
