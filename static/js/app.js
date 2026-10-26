document.addEventListener("DOMContentLoaded", () => {
  let cartCount = 0;
  const cartCountEl = document.getElementById("cartCount");
  const toast = document.getElementById("toastMessage");

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 2200);
  }

  document.querySelectorAll(".add-button").forEach((button) => {
    button.addEventListener("click", () => {
      cartCount += 1;
      cartCountEl.textContent = cartCount;
      const name = button.dataset.productName || "Product";
      showToast(`${name} added to demo cart`);
    });
  });

  document.querySelectorAll(".heart-button").forEach((button) => {
    button.addEventListener("click", () => {
      const saved = button.classList.toggle("saved");
      button.textContent = saved ? "♥" : "♡";
      button.style.color = saved ? "#d45c55" : "";
      showToast(saved ? "Saved for later (demo)" : "Removed from saved items");
    });
  });

  document.getElementById("cartButton").addEventListener("click", () => {
    showToast(`Demo cart: ${cartCount} item(s). Full cart arrives in a later milestone.`);
  });
});
