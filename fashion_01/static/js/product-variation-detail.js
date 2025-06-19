

document.addEventListener("DOMContentLoaded", function () {
  const setItemsSelect = document.getElementById("set-items");
  const customizeToggle = document.getElementById("customize-toggle");
  const customizationFields = document.getElementById("customization-fields");
  const customizationGroups = document.querySelectorAll(".customization-group");

  const monogramCheckbox = document.getElementById("enable-jacket-monogram");
  const monogramFields = document.getElementById("jacket-monogram-fields");

  const vestCheckbox = document.getElementById("enable-vest-customization");
  const vestFields = document.getElementById("vest-customization-fields");

  // Shirt checkbox and fields
  const shirtCheckbox = document.getElementById("enable-shirt-customization");
  const shirtFields = document.getElementById("shirt-customization-fields");

  const totalPriceEl = document.getElementById("total-price");
  const basePrice = parseFloat("{{ product.price|floatformat:2 }}");
  const MONOGRAM_PRICE = parseFloat("{{ monogram_price }}");
  const VEST_PRICE = parseFloat("{{ vest_price }}");
  const SHIRT_PRICE = parseFloat("{{ shirt_price }}");

  let currentTarget = "";

  // Monogram checkbox toggle
  if (monogramCheckbox && monogramFields) {
    monogramCheckbox.addEventListener("change", () => {
      monogramFields.style.display = monogramCheckbox.checked ? "block" : "none";
      calculateTotal();
    });
  }

  // Vest checkbox toggle
  if (vestCheckbox && vestFields) {
    vestCheckbox.addEventListener("change", () => {
      vestFields.style.display = vestCheckbox.checked ? "block" : "none";
      calculateTotal();
    });
  }

  // Shirt checkbox toggle
  if (shirtCheckbox && shirtFields) {
    shirtCheckbox.addEventListener("change", () => {
      shirtFields.style.display = shirtCheckbox.checked ? "block" : "none";
      calculateTotal();
    });
  }

  // Toggle main customization panel
  customizeToggle.addEventListener("click", function () {
    const isHidden = customizationFields.style.display === "none";
    customizationFields.style.display = isHidden ? "block" : "none";
    updateCustomizationGroups();
    calculateTotal();
  });

  // Show correct customization group based on selected set item
  function updateCustomizationGroups() {
    const selectedSet = setItemsSelect.options[setItemsSelect.selectedIndex];
    currentTarget = selectedSet.dataset.target;

    customizationGroups.forEach((group) => {
      group.style.display = group.dataset.target === currentTarget ? "block" : "none";
    });

    if (currentTarget === "jacket") {
      monogramFields.style.display = monogramCheckbox.checked ? "block" : "none";
    } else {
      monogramFields.style.display = "none";
      if(monogramCheckbox) monogramCheckbox.checked = false;
    }
  }

  // Calculate total price
  function calculateTotal() {
    let total = basePrice;

    // Add set item price
    const selectedSet = setItemsSelect.options[setItemsSelect.selectedIndex];
    total += parseFloat(selectedSet.dataset.price || 0);

    // Add customization prices only if customization panel is visible
    if (customizationFields.style.display !== "none") {
      const activeGroup = document.querySelector(`.customization-group[data-target="${currentTarget}"]`);
      if (activeGroup) {
        const checkedRadios = activeGroup.querySelectorAll('input[type="radio"]:checked');
        checkedRadios.forEach((radio) => {
          total += parseFloat(radio.dataset.price || 0);
        });
      }

      // Monogram prices (jacket only)
      if (currentTarget === "jacket" && monogramCheckbox && monogramCheckbox.checked) {
        total += MONOGRAM_PRICE;
        const monogramRadios = monogramFields.querySelectorAll('input[type="radio"]:checked');
        monogramRadios.forEach((radio) => {
          total += parseFloat(radio.dataset.price || 0);
        });
      }
    }

    // Add vest price if checked (always)
    if (vestCheckbox && vestCheckbox.checked) {
      total += VEST_PRICE;
    }

    // Add shirt price if checked (always)
    if (shirtCheckbox && shirtCheckbox.checked) {
      total += SHIRT_PRICE;
    }

    totalPriceEl.textContent = total.toFixed(2);
  }

  // Set item dropdown change
  setItemsSelect.addEventListener("change", function () {
    updateCustomizationGroups();
    calculateTotal();
  });

  // Customization radio buttons change
  document.querySelectorAll('#customization-fields input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", calculateTotal);
  });

  // Initialize on page load
  updateCustomizationGroups();
  calculateTotal();
});
