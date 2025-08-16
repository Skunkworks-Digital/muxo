document.addEventListener('DOMContentLoaded', () => {
  const year = document.getElementById('year');
  if (year) {
    year.textContent = new Date().getFullYear().toString();
  }

  const btn = document.getElementById('back-to-top');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 200) {
      btn.style.display = 'block';
    } else {
      btn.style.display = 'none';
    }
  });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
