document.addEventListener("DOMContentLoaded", () => {
    // Interactive color selection on product detail page
    const colorDots = document.querySelectorAll(".color-dot");
    colorDots.forEach(dot => {
        dot.addEventListener("click", () => {
            colorDots.forEach(d => d.style.border = "none");
            dot.style.border = "2px solid #2c3e50";
        });
    });

    // Simple add to cart notification feedback
    const addCartBtn = document.getElementById("add-to-cart-btn");
    if (addCartBtn) {
        addCartBtn.addEventListener("click", () => {
            alert("Product added to your cart!");
        });
    }
});