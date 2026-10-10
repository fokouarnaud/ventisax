// Progressive enhancement: navigation stays usable if JavaScript is unavailable.
(() => {
  const menu = document.querySelector('.main-nav');
  const toggle = document.querySelector('.menu-toggle');
  const mobile = window.matchMedia('(max-width: 960px)');
  const setMenu = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    menu.hidden = mobile.matches && !open;
  };
  const resetMenu = () => {
    // Never leave keyboard focus inside a menu that becomes hidden on resize.
    const hadFocus = menu.contains(document.activeElement);
    const toggleHadFocus = document.activeElement === toggle;
    toggle.hidden = !mobile.matches;
    setMenu(false);
    if (mobile.matches && hadFocus) toggle.focus();
    if (!mobile.matches && toggleHadFocus) document.querySelector('.brand').focus();
  };
  if (menu && toggle) {
    resetMenu();
    mobile.addEventListener('change', resetMenu);
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && mobile.matches && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });
    menu.addEventListener('click', (event) => {
      if (event.target.closest('a') && mobile.matches) setMenu(false);
    });
  }

  const banner = document.querySelector('.preview-banner');
  const dismiss = document.querySelector('[data-dismiss-preview]');
  if (banner && dismiss) {
    dismiss.hidden = false;
    try { banner.hidden = sessionStorage.getItem('ventisax-preview-dismissed') === '1'; } catch (_) { /* Storage is optional. */ }
    dismiss.addEventListener('click', () => {
      banner.hidden = true;
      try { sessionStorage.setItem('ventisax-preview-dismissed', '1'); } catch (_) { /* Keep dismissal usable without storage. */ }
      (toggle && !toggle.hidden ? toggle : document.querySelector('.brand')).focus();
    });
  }

  const topLink = document.querySelector('.back-to-top');
  const top = document.getElementById('page-top');
  if (topLink && top) {
    const updateTopLink = () => { topLink.hidden = window.scrollY < 500; };
    window.addEventListener('scroll', updateTopLink, { passive: true });
    updateTopLink();
    topLink.addEventListener('click', (event) => {
      event.preventDefault();
      top.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    });
  }
})();
