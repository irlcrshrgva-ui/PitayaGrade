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

  const apk = document.querySelector('[data-apk-link]');
  const setText = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  };
  if (apk) {
    const metadataUrl = new URL('../downloads/release.json', window.location.href);
    fetch(metadataUrl, { cache: 'no-store' }).then(response => {
      if (!response.ok) throw new Error('Build metadata unavailable');
      return response.json();
    }).then(release => {
      if (!release || !release.sha256 || !release.bytes || !release.commit || !release.builtAt) throw new Error('Build metadata incomplete');
      setText('[data-build-version]', `Version ${release.version}`);
      setText('[data-apk-size]', `${(release.bytes / 1024 / 1024).toFixed(1)} MB`);
      setText('[data-build-date]', `Built ${new Date(release.builtAt).toLocaleDateString()}`);
      setText('[data-build-commit]', `Source ${release.commit.slice(0, 7)}`);
      setText('[data-build-sha]', release.sha256);
      setText('[data-release-status]', release.signedRelease
        ? 'Signed release build. Verify the checksum after downloading.'
        : 'Unsigned debug build for supervised testing—not a Play Store release.');
      const checksumCard = document.querySelector('[data-checksum-card]');
      if (checksumCard) checksumCard.hidden = false;
      const copyButton = document.querySelector('[data-copy-checksum]');
      copyButton?.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(release.sha256);
          copyButton.textContent = 'Copied';
          window.setTimeout(() => { copyButton.textContent = 'Copy checksum'; }, 1800);
        } catch (_) {
          copyButton.textContent = 'Select checksum above';
        }
      });
    }).catch(() => {
      setText('[data-apk-size]', 'Size shown during download');
      setText('[data-build-date]', 'Build details unavailable');
      setText('[data-build-commit]', 'Testing channel');
      setText('[data-release-status]', 'The APK can still be downloaded, but its verification details could not be loaded.');
    });
  }

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
