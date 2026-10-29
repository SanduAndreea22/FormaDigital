// Disable the submit button after the first click so a double click cannot send the form twice.
document.addEventListener('submit', function (event) {
  var form = event.target;
  if (form.dataset.submitted) {
    event.preventDefault();
    return;
  }
  form.dataset.submitted = '1';
  var button = form.querySelector('button[type="submit"]');
  if (button) {
    button.dataset.label = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending…';
  }
});

// Coming back with the browser's back button must not leave the form locked.
window.addEventListener('pageshow', function (event) {
  if (!event.persisted) return;
  document.querySelectorAll('form[data-submitted]').forEach(function (form) {
    delete form.dataset.submitted;
    var button = form.querySelector('button[type="submit"]');
    if (button && button.dataset.label) {
      button.disabled = false;
      button.textContent = button.dataset.label;
    }
  });
});
