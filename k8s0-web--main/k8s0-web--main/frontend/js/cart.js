document.addEventListener('DOMContentLoaded', () => {
    loadCart();
});

async function loadCart() {
    const container = document.getElementById('cartContainer');
    try {
        const cart = await Api.cart.getCart();
        
        if (!cart.items || cart.items.length === 0) {
            container.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-16 glass rounded-2xl">
                    <i class="fa-solid fa-cart-shopping text-6xl text-gray-600 mb-6"></i>
                    <h2 class="text-2xl font-serif mb-2">Giỏ hàng trống</h2>
                    <p class="text-gray-400 mb-8">Bạn chưa có sản phẩm nào trong giỏ hàng.</p>
                    <a href="index.html#products" class="btn-primary px-8 py-3 rounded-full font-medium">Khám Phá Sản Phẩm</a>
                </div>
            `;
            return;
        }

        let subtotal = 0;
        
        const itemsHtml = cart.items.map(item => {
            const id = item.product_id || item.id;
            const name = item.product_name || item.name || 'Sản phẩm';
            const price = item.unit_price !== undefined ? item.unit_price : (item.price || 0);
            const img = item.image || item.img || 'images/cat-cues.jpg';
            const itemTotal = price * item.quantity;
            subtotal += itemTotal;
            return `
                <div class="glass p-4 rounded-xl flex gap-4 items-center mb-4 transition-all hover:border-gold/50" id="cart-item-${id}">
                    <img src="${img}" class="w-24 h-24 object-cover rounded-lg bg-black/50" onerror="this.src='images/cat-cues.jpg'">
                    <div class="flex-grow">
                        <a href="product.html?id=${id}" class="font-medium text-white hover:text-gold line-clamp-1">${name}</a>
                        <div class="text-gold font-semibold mt-1">${App.formatPrice(price)}</div>
                    </div>
                    <div class="flex items-center border border-gray-700 rounded bg-dark/50 mx-2">
                        <button onclick="updateCartQty('${id}', ${item.quantity - 1})" class="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white"><i class="fa-solid fa-minus text-xs"></i></button>
                        <span class="w-10 text-center text-sm font-medium">${item.quantity}</span>
                        <button onclick="updateCartQty('${id}', ${item.quantity + 1})" class="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white"><i class="fa-solid fa-plus text-xs"></i></button>
                    </div>
                    <div class="text-right min-w-[100px] hidden sm:block font-bold">
                        ${App.formatPrice(itemTotal)}
                    </div>
                    <button onclick="removeCartItem('${id}')" class="w-10 h-10 flex items-center justify-center text-gray-500 hover:text-red-500 transition rounded-full hover:bg-red-500/10">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            `;
        }).join('');

        const summaryHtml = `
            <div class="lg:col-span-1">
                <div class="glass p-6 rounded-2xl sticky top-28">
                    <h3 class="font-serif text-xl font-bold mb-6 border-b border-gray-700 pb-4">Tổng Đơn Hàng</h3>
                    
                    <div class="flex justify-between mb-4 text-gray-300">
                        <span>Tạm tính</span>
                        <span class="font-medium">${App.formatPrice(subtotal)}</span>
                    </div>
                    <div class="flex justify-between mb-6 text-gray-300">
                        <span>Vận chuyển</span>
                        <span>Miễn phí</span>
                    </div>
                    
                    <div class="flex justify-between items-center py-4 border-t border-gray-700 mb-8">
                        <span class="font-bold">Tổng cộng</span>
                        <span class="font-bold text-2xl text-gold">${App.formatPrice(subtotal)}</span>
                    </div>
                    
                    <a href="checkout.html" class="block w-full text-center btn-primary py-3.5 rounded-xl font-bold uppercase tracking-wide">
                        Tiến Hành Thanh Toán
                    </a>
                </div>
            </div>
        `;

        container.innerHTML = `
            <div class="lg:col-span-2">
                ${itemsHtml}
            </div>
            ${summaryHtml}
        `;

    } catch (e) {
        showToast('Lỗi tải giỏ hàng', 'error');
    }
}

async function updateCartQty(id, newQty) {
    if (newQty < 1) {
        removeCartItem(id);
        return;
    }
    await Api.cart.updateQuantity(id, newQty);
    window.dispatchEvent(new Event('cartUpdated'));
    loadCart();
}

async function removeCartItem(id) {
    if(confirm('Bạn có chắc muốn xóa sản phẩm này khỏi giỏ hàng?')) {
        await Api.cart.removeItem(id);
        window.dispatchEvent(new Event('cartUpdated'));
        showToast('Đã xóa sản phẩm');
        loadCart();
    }
}
