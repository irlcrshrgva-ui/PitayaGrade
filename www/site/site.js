(() => {
  document.querySelectorAll('a[href="../"]').forEach(link => {
    if (/open web app|try the web app/i.test(link.textContent || '')) {
      link.href = '../reset.html';
      link.textContent = 'Open latest web app';
    }
  });

  const menu = document.querySelector('.menu-button');
  const links = document.querySelector('.nav-links');
  menu?.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  links?.addEventListener('click', event => {
    if (event.target.closest('a')) {
      links.classList.remove('open');
      menu?.setAttribute('aria-expanded', 'false');
    }
  });

  const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: .12 }) : null;
  document.querySelectorAll('.reveal').forEach(item => observer ? observer.observe(item) : item.classList.add('visible'));

  const copyButton = document.querySelector('[data-copy-checksum]');
  copyButton?.addEventListener('click', async () => {
    const checksum = document.querySelector('[data-build-sha]').textContent.trim();
    try {
      await navigator.clipboard.writeText(checksum);
      copyButton.textContent = 'Copied';
      window.setTimeout(() => { copyButton.textContent = 'Copy checksum'; }, 1800);
    } catch (_) {
      copyButton.textContent = 'Select checksum above';
    }
  });

  const form = document.querySelector('#supportForm');
  form?.addEventListener('submit', event => {
    event.preventDefault();
    const data = new FormData(form);
    const type = String(data.get('type') || 'Feedback');
    const subject = String(data.get('subject') || 'PitayaGrade feedback').trim();
    const details = String(data.get('details') || '').trim();
    const body = `### ${type}\n\n${details}\n\n---\nSubmitted from the PitayaGrade website.`;
    const url = new URL('https://github.com/irlcrshrgva-ui/PitayaGrade/issues/new');
    url.searchParams.set('title', subject);
    url.searchParams.set('body', body);
    window.open(url, '_blank', 'noopener,noreferrer');
  });

  document.querySelectorAll('[data-year]').forEach(node => { node.textContent = new Date().getFullYear(); });
})();
