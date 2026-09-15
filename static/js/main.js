function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
  const mobileToggle = document.getElementById('mobile-toggle');
  const mobileDrawer = document.getElementById('mobile-drawer');
  const mobileClose = document.getElementById('mobile-close');

  if (mobileToggle && mobileDrawer) {
    mobileToggle.addEventListener('click', function() {
      mobileDrawer.classList.add('open');
      document.body.style.overflow = 'hidden';
    });
  }

  if (mobileClose && mobileDrawer) {
    mobileClose.addEventListener('click', function() {
      mobileDrawer.classList.remove('open');
      document.body.style.overflow = '';
    });
  }

  if (mobileDrawer) {
    mobileDrawer.addEventListener('click', function(e) {
      if (e.target === mobileDrawer) {
        mobileDrawer.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  }

  const dropdownToggles = document.querySelectorAll('[data-dropdown-toggle]');
  dropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
      const parent = this.closest('.dropdown');
      if (parent) {
        parent.classList.toggle('open');
      }
    });
  });

  document.addEventListener('click', function() {
    document.querySelectorAll('.dropdown.open').forEach(dropdown => {
      dropdown.classList.remove('open');
    });
  });

  const tabLinks = document.querySelectorAll('.tab-link');
  tabLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('data-tab');
      const tabsContainer = this.closest('.tabs-wrapper') || document;
      
      tabsContainer.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
      tabsContainer.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      this.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });

  document.querySelectorAll('form[data-loading]').forEach(form => {
    form.addEventListener('submit', function() {
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        const loadingText = submitBtn.getAttribute('data-loading-text') || '⏳ Amal bajarilmoqda...';
        submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
        submitBtn.innerHTML = loadingText;
        submitBtn.disabled = true;
      }
    });
  });

  const filterToggle = document.getElementById('filter-drawer-toggle');
  const filterCard = document.getElementById('marketplace-filter-card');
  const filterClose = document.getElementById('filter-close-btn');
  const filterBackdrop = document.getElementById('filter-backdrop');

  function openFilterDrawer() {
    if (filterCard) filterCard.classList.add('open');
    if (filterBackdrop) filterBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeFilterDrawer() {
    if (filterCard) filterCard.classList.remove('open');
    if (filterBackdrop) filterBackdrop.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (filterToggle) {
    filterToggle.addEventListener('click', openFilterDrawer);
  }
  if (filterClose) {
    filterClose.addEventListener('click', closeFilterDrawer);
  }
  if (filterBackdrop) {
    filterBackdrop.addEventListener('click', closeFilterDrawer);
  }

  const djangoMessages = document.querySelectorAll('.django-message-data');
  djangoMessages.forEach(msg => {
    const text = msg.getAttribute('data-message');
    const level = msg.getAttribute('data-level');
    let type = 'info';
    if (level === 'success') type = 'success';
    else if (level === 'error') type = 'error';
    else if (level === 'warning') type = 'warning';
    
    if (window.showToast && text) {
      window.showToast(text, type);
    }
  });

  function updateThemeUI(theme) {
    const isDark = theme === 'dark';
    document.querySelectorAll('.theme-icon-light').forEach(el => {
      el.style.display = isDark ? 'none' : 'inline-block';
    });
    document.querySelectorAll('.theme-icon-dark').forEach(el => {
      el.style.display = isDark ? 'inline-block' : 'none';
    });
    document.querySelectorAll('.theme-toggle-label').forEach(el => {
      el.textContent = isDark ? 'Kunduzgi rejim' : 'Tungi rejim';
    });
  }

  const currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  updateThemeUI(currentTheme);

  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const isCurrentlyDark = document.documentElement.getAttribute('data-theme') === 'dark';
      const nextTheme = isCurrentlyDark ? 'light' : 'dark';
      if (nextTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.removeAttribute('data-theme');
      }
      try {
        localStorage.setItem('codora_theme', nextTheme);
      } catch (err) {}
      updateThemeUI(nextTheme);
      if (typeof renderAppleEmojis === 'function') {
        renderAppleEmojis(document.body);
      }
    });
  });

  const avatarInput = document.getElementById('avatar');
  if (avatarInput) {
    avatarInput.addEventListener('change', function() {
      const file = this.files && this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(evt) {
          const container = document.getElementById('avatar-preview-container');
          let previewImg = document.getElementById('avatar-preview-img');
          const previewPlaceholder = document.getElementById('avatar-preview-placeholder');
          if (previewImg) {
            previewImg.src = evt.target.result;
            previewImg.style.display = 'block';
            if (previewPlaceholder) previewPlaceholder.style.display = 'none';
          } else if (container) {
            if (previewPlaceholder) previewPlaceholder.style.display = 'none';
            previewImg = document.createElement('img');
            previewImg.id = 'avatar-preview-img';
            previewImg.src = evt.target.result;
            previewImg.alt = 'Avatar';
            previewImg.style.width = '88px';
            previewImg.style.height = '88px';
            previewImg.style.borderRadius = 'var(--radius-full)';
            previewImg.style.objectFit = 'cover';
            previewImg.style.border = '2px solid var(--accent)';
            previewImg.style.boxShadow = 'var(--shadow-sm)';
            container.appendChild(previewImg);
          }
        };
        reader.readAsDataURL(file);
      }
    });
  }

  document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function() {
      const file = this.files && this.files[0];
      if (!file) return;

      const maxSizeMB = parseFloat(this.getAttribute('data-max-size'));
      const allowedExtAttr = this.getAttribute('data-allowed-ext');

      if (maxSizeMB) {
        const maxBytes = maxSizeMB * 1024 * 1024;
        if (file.size > maxBytes) {
          const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
          if (window.showToast) {
            window.showToast(`Fayl hajmi juda katta (${fileSizeMB} MB). Maksimal limit: ${maxSizeMB} MB`, 'error');
          }
          this.value = '';
          return;
        }
      }

      if (allowedExtAttr) {
        const allowedExts = allowedExtAttr.split(',').map(s => s.trim().toLowerCase());
        const fileNameParts = file.name.split('.');
        const fileExt = fileNameParts.length > 1 ? fileNameParts.pop().toLowerCase() : '';
        if (!allowedExts.includes(fileExt)) {
          if (window.showToast) {
            window.showToast(`Noto‘g‘ri fayl formati (.${fileExt}). Faqat ${allowedExts.join(', ').toUpperCase()} qabul qilinadi`, 'error');
          }
          this.value = '';
          return;
        }
      }
    });
  });

  const thumbInput = document.getElementById('id_thumbnail');
  const thumbPreview = document.getElementById('thumbnail-preview');
  if (thumbInput && thumbPreview) {
    thumbInput.addEventListener('change', function() {
      const file = this.files && this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          thumbPreview.src = e.target.result;
          thumbPreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
      } else {
        thumbPreview.style.display = 'none';
      }
    });
  }

  document.querySelectorAll('.upload-dropzone').forEach(zone => {
    const input = zone.querySelector('input[type="file"]');
    const textEl = zone.querySelector('.upload-dropzone-text');
    if (!input) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      zone.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      zone.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('dragover');
      });
    });

    zone.addEventListener('drop', e => {
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        const changeEvent = new Event('change', { bubbles: true });
        input.dispatchEvent(changeEvent);
      }
    });

    input.addEventListener('change', function() {
      if (this.files && this.files.length > 0 && textEl) {
        textEl.textContent = 'Tanlandi: ' + this.files[0].name;
      }
    });
  });

  const starControls = document.querySelectorAll('.star-rating-control');
  starControls.forEach(ctrl => {
    const input = ctrl.querySelector('input[type="hidden"]');
    const stars = ctrl.querySelectorAll('.star-rating-star');
    
    function setRating(val) {
      if (input) input.value = val;
      stars.forEach(s => {
        const sVal = parseInt(s.getAttribute('data-value'), 10);
        if (sVal <= val) {
          s.classList.add('active');
        } else {
          s.classList.remove('active');
        }
      });
    }

    stars.forEach(star => {
      star.addEventListener('mouseenter', function() {
        const val = parseInt(this.getAttribute('data-value'), 10);
        stars.forEach(s => {
          const sVal = parseInt(s.getAttribute('data-value'), 10);
          if (sVal <= val) s.classList.add('hover');
          else s.classList.remove('hover');
        });
      });

      star.addEventListener('click', function() {
        const val = parseInt(this.getAttribute('data-value'), 10);
        setRating(val);
      });
    });

    ctrl.addEventListener('mouseleave', function() {
      stars.forEach(s => s.classList.remove('hover'));
    });

    if (input && input.value) {
      setRating(parseInt(input.value, 10));
    }
  });

  const lightbox = document.getElementById('lightbox-modal');
  const lightboxImg = document.getElementById('lightbox-img');
  const lightboxClose = document.getElementById('lightbox-close');

  window.openLightbox = function(src) {
    if (lightbox && lightboxImg) {
      lightboxImg.src = src;
      lightbox.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  };

  window.closeLightbox = function() {
    if (lightbox) {
      lightbox.classList.remove('open');
      document.body.style.overflow = '';
    }
  };

  if (lightboxClose) {
    lightboxClose.addEventListener('click', window.closeLightbox);
  }
  if (lightbox) {
    lightbox.addEventListener('click', function(e) {
      if (e.target === lightbox) window.closeLightbox();
    });
  }

  const liveItems = document.querySelectorAll('.hero-showcase-item');
  if (liveItems.length > 0) {
    let currentHighlight = 0;
    setInterval(() => {
      liveItems.forEach((item, idx) => {
        if (idx === currentHighlight) {
          item.classList.add('highlight-pulse');
        } else {
          item.classList.remove('highlight-pulse');
        }
      });
      currentHighlight = (currentHighlight + 1) % liveItems.length;
    }, 3000);
  }

  if (typeof renderAppleEmojis === 'function') {
    renderAppleEmojis(document.body);
  }
});

const emojiCodeMap = {
  '🚀': '1f680',
  '⚡': '26a1',
  '💎': '1f48e',
  '✨': '2728',
  '🛒': '1f6d2',
  '❤️': '2764-fe0f',
  '🔥': '1f525',
  '⭐': '2b50',
  '📦': '1f4e6',
  '🎯': '1f3af',
  '🛡️': '1f6e1-fe0f',
  '🛡': '1f6e1-fe0f',
  '🤖': '1f916',
  '📱': '1f4f1',
  '🎨': '1f3a8',
  '💻': '1f4bb',
  '🛍️': '1f6cd-fe0f',
  '🛍': '1f6cd-fe0f',
  '👁️': '1f441-fe0f',
  '👁': '1f441-fe0f',
  '⚙️': '2699-fe0f',
  '⚙': '2699-fe0f',
  '⬇️': '2b07-fe0f',
  '⬇': '2b07-fe0f',
  '✏️': '270f-fe0f',
  '✏': '270f-fe0f',
  '🗑️': '1f5d1-fe0f',
  '🗑': '1f5d1-fe0f',
  '🔍': '1f50d',
  '👤': '1f464',
  '📁': '1f4c1',
  '💼': '1f4bc',
  '🚪': '1f6aa',
  '🔑': '1f511',
  '🏠': '1f3e0',
  '🔔': '1f514',
  '⏳': '23f3',
  'ℹ️': '2139-fe0f',
  'ℹ': '2139-fe0f',
  '🎉': '1f389',
  '✅': '2705',
  '❌': '274c',
  '🔒': '1f512',
  '🎖️': '1f396-fe0f',
  '🎖': '1f396-fe0f'
};

function getEmojiHex(emoji) {
  if (emojiCodeMap[emoji]) return emojiCodeMap[emoji];
  const pts = [];
  for (let i = 0; i < emoji.length; i++) {
    const code = emoji.codePointAt(i);
    if (code > 0xffff) i++;
    if (code !== 0xfe0e) {
      pts.push(code.toString(16).toLowerCase());
    }
  }
  return pts.join('-');
}

function renderAppleEmojis(rootNode) {
  const root = rootNode || document.body;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: function(node) {
      if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      const tag = parent.tagName.toLowerCase();
      if (tag === 'script' || tag === 'style' || tag === 'textarea' || tag === 'input' || tag === 'code' || parent.classList.contains('apple-emoji')) {
        return NodeFilter.FILTER_REJECT;
      }
      return /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });

  const nodesToProcess = [];
  while (walker.nextNode()) {
    nodesToProcess.push(walker.currentNode);
  }

  const emojiRegex = /(\p{Extended_Pictographic}(?:\uFE0F|\u200D\p{Extended_Pictographic})*)/gu;

  nodesToProcess.forEach(textNode => {
    const text = textNode.nodeValue;
    if (!emojiRegex.test(text)) return;
    emojiRegex.lastIndex = 0;
    
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let match;

    while ((match = emojiRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
      }
      const emojiChar = match[0];
      const hex = getEmojiHex(emojiChar);
      const img = document.createElement('img');
      img.className = 'apple-emoji';
      img.alt = emojiChar;
      img.loading = 'lazy';
      img.draggable = false;
      img.src = 'https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/' + hex + '.png';
      img.onerror = function() {
        this.replaceWith(document.createTextNode(this.alt));
      };
      fragment.appendChild(img);
      lastIndex = emojiRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
    }

    if (textNode.parentNode) {
      textNode.parentNode.replaceChild(fragment, textNode);
    }
  });
}
window.renderAppleEmojis = renderAppleEmojis;
