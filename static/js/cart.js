async function toggleWishlist(productId, btnElement) {
  const csrftoken = getCookie('csrftoken');

  try {
    const response = await fetch(`/wishlist/toggle/${productId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    const data = await response.json();
    if (response.ok) {
      if (btnElement) {
        if (data.action === 'added') {
          btnElement.classList.add('active');
        } else {
          btnElement.classList.remove('active');
        }
      }
      
      const badge = document.getElementById('wishlist-badge');
      if (badge) {
        badge.innerText = data.total_count;
        badge.style.display = data.total_count > 0 ? 'flex' : 'none';
      }

      if (window.showToast) {
        window.showToast(data.message, data.action === 'added' ? 'success' : 'info');
      }
    } else {
      if (response.status === 401 || data.login_required) {
        if (window.showToast) {
          window.showToast(data.error || "Sevimlilarga qo‘shish uchun avval hisobingizga kiring.", "warning");
        }
        setTimeout(() => {
          window.location.href = data.redirect_url || '/login/';
        }, 800);
      } else if (window.showToast) {
        window.showToast(data.error || 'Amalni bajarib bo‘lmadi.', 'error');
      }
    }
  } catch (error) {
    if (window.showToast) {
      window.showToast('Tarmoq xatosi yuz berdi.', 'error');
    }
  }
}

async function addToCart(productId, redirect = false) {
  const csrftoken = getCookie('csrftoken');
  try {
    const response = await fetch(`/cart/add/${productId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    const data = await response.json();
    if (response.ok) {
      const badge = document.getElementById('cart-badge');
      if (badge) {
        badge.innerText = data.total_items;
        badge.style.display = data.total_items > 0 ? 'flex' : 'none';
      }

      const mobileBadge = document.getElementById('mobile-cart-badge');
      if (mobileBadge) {
        mobileBadge.innerText = data.total_items;
        mobileBadge.style.display = data.total_items > 0 ? 'flex' : 'none';
      }

      if (redirect) {
        window.location.href = '/checkout/';
      } else {
        if (window.showToast) {
          window.showToast(data.message, 'success');
        }
      }
    } else {
      if (response.status === 401 || data.login_required) {
        if (window.showToast) {
          window.showToast(data.error || "Savatga qo‘shish uchun avval hisobingizga kiring.", "warning");
        }
        setTimeout(() => {
          window.location.href = data.redirect_url || '/login/';
        }, 800);
      } else if (data.owned) {
        if (window.showToast) {
          window.showToast("Siz ushbu mahsulotni avval xarid qilgansiz.", "info");
        }
        setTimeout(() => {
          window.location.href = '/library/';
        }, 800);
      } else {
        if (window.showToast) {
          window.showToast(data.error || 'Mahsulotni savatga qo‘shib bo‘lmadi.', 'warning');
        }
      }
    }
  } catch (err) {
    if (window.showToast) {
      window.showToast('Xatolik yuz berdi.', 'error');
    }
  }
}

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-wishlist-toggle]').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      const productId = this.getAttribute('data-wishlist-toggle');
      toggleWishlist(productId, this);
    });
  });

  document.querySelectorAll('[data-add-cart]').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const productId = this.getAttribute('data-add-cart');
      const direct = this.getAttribute('data-direct') === 'true';
      addToCart(productId, direct);
    });
  });
});
