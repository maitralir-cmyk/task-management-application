// Small client-side enhancement: dismiss flash messages after a short delay.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.style.transition = "opacity .35s ease";
      message.style.opacity = "0";
      window.setTimeout(() => message.remove(), 400);
    }, 4500);
  });
});
