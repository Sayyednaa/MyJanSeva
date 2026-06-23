/* ==========================================================================
   Ration Card Studio - Application Logic & IndexedDB Operations
   ========================================================================== */

// Global App State
let currentEditingId = null; 
let printQueue = []; 
let historyCards = []; 
const placeholderAvatar = window.PLACEHOLDER_AVATAR_URL || '/static/id_cards/farmer_id/placeholder-avatar.png';
let selectedDesign = '1';

// Charge Wallet on Backend
function chargeWallet(slug, quantity) {
    if (!window.WALLET_CHARGE_URL || !window.CSRF_TOKEN) {
        return Promise.reject(new Error('Wallet integration not configured.'));
    }
    let formData = new FormData();
    formData.append('service_slug', slug);
    formData.append('quantity', quantity);
    formData.append('csrfmiddlewaretoken', window.CSRF_TOKEN);
    return fetch(window.WALLET_CHARGE_URL, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',  
    })
    .then(r => {
        const contentType = r.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            let err = new Error('Server rejected the request. Please refresh the page and try again. (Status: ' + r.status + ')');
            err.isInsufficientBalance = false;
            throw err;
        }
        return r.json();
    })
    .then(json => {
        if(json.status === 'error') {
            let err = new Error(json.message);
            if (json.code === 'insufficient_balance') {
                err.isInsufficientBalance = true;
                err.redirectUrl = json.redirect_url || '/wallet/topup/';
            }
            throw err;
        }
        return json;
    });
}

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', async () => {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  try {
    await loadHistory();
    loadPrintQueueFromStorage();
  } catch (error) {
    console.error('Initialization failed:', error);
  }

  resetForm();
  setupEventListeners();
});

/* ==========================================================================
   BACKEND DATABASE LAYER
   ========================================================================== */
function getAllCards() {
  if (!window.RATION_LIST_URL) return Promise.resolve([]);
  return fetch(window.RATION_LIST_URL)
    .then(r => {
      if (!r.ok) throw new Error('HTTP error ' + r.status);
      return r.json();
    });
}

function saveCard(cardData) {
  if (!window.RATION_SAVE_URL) return Promise.reject(new Error('Save URL not configured.'));
  return fetch(window.RATION_SAVE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window.CSRF_TOKEN
    },
    body: JSON.stringify(cardData)
  })
  .then(r => {
    if (!r.ok) throw new Error('HTTP error ' + r.status);
    return r.json();
  })
  .then(res => {
    if (res.status === 'error') {
      let err = new Error(res.message);
      if (res.code === 'insufficient_balance') {
        err.isInsufficientBalance = true;
        err.redirectUrl = res.redirect_url || '/wallet/topup/';
      }
      throw err;
    }
    return res.card.id;
  });
}

function deleteCardFromDB(id) {
  if (!window.RATION_DELETE_URL) return Promise.reject(new Error('Delete URL not configured.'));
  return fetch(window.RATION_DELETE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window.CSRF_TOKEN
    },
    body: JSON.stringify({ id: id })
  })
  .then(r => {
    if (!r.ok) throw new Error('HTTP error ' + r.status);
    return r.json();
  })
  .then(res => {
    if (res.status === 'error') throw new Error(res.message);
    return;
  });
}

function getCardById(id) {
  if (!window.RATION_DETAIL_URL_BASE) return Promise.resolve(null);
  return fetch(window.RATION_DETAIL_URL_BASE + id + '/')
    .then(r => {
      if (r.status === 404) return null;
      if (!r.ok) throw new Error('HTTP error ' + r.status);
      return r.json();
    });
}

async function processPrintCharge(card) {
  const FREE_PRINTS = 2;
  if (!card.id) {
    return card;
  }

  const fresh = await getCardById(card.id);
  if (!fresh) return card; 

  const currentCount = fresh.printCount || 0;
  const newCount = currentCount + 1;

  if (currentCount >= FREE_PRINTS) {
    await chargeWallet('ration-card', 1); 
  }

  fresh.printCount = newCount;
  await saveCard(fresh);

  const idx = historyCards.findIndex(c => c.id === fresh.id);
  if (idx !== -1) historyCards[idx].printCount = newCount;

  return fresh;
}

/* ==========================================================================
   APP EVENT LISTENERS
   ========================================================================== */
function setupEventListeners() {
  const navButtons = document.querySelectorAll('.nav-btn');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      switchTab(tabName);
    });
  });

  document.getElementById('add-table-row').addEventListener('click', () => {
    addFamilyTableRow();
  });

  const syncFields = ['ration-card-number', 'scheme-name', 'head-of-family', 'issue-date', 'fare-shop-number', 'mobile-number', 'address'];
  syncFields.forEach(fieldId => {
    const el = document.getElementById(fieldId);
    el.addEventListener('input', updateLivePreview);
    el.addEventListener('change', updateLivePreview);
  });

  const photoInput = document.getElementById('photo-upload');
  const uploadZone = document.querySelector('.photo-upload-zone');
  
  photoInput.addEventListener('change', handlePhotoSelection);
  
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = 'var(--primary-light)';
    uploadZone.style.backgroundColor = 'rgba(63, 81, 181, 0.05)';
  });
  
  uploadZone.addEventListener('dragleave', () => {
    uploadZone.style.borderColor = '#cbd5e1';
    uploadZone.style.backgroundColor = '#f8fafc';
  });
  
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '#cbd5e1';
    uploadZone.style.backgroundColor = '#f8fafc';
    if (e.dataTransfer.files.length) {
      photoInput.files = e.dataTransfer.files;
      handlePhotoSelection();
    }
  });

  document.querySelector('.remove-photo-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    removeUploadedPhoto();
  });

  document.getElementById('clear-form').addEventListener('click', () => {
    if(confirm('Are you sure you want to clear the form?')) {
      resetForm();
    }
  });

  document.getElementById('ration-form').addEventListener('submit', handleFormSubmit);
  document.getElementById('history-search').addEventListener('input', filterHistoryList);
  document.getElementById('select-all-records').addEventListener('change', toggleAllRecordsSelection);
  document.getElementById('btn-bulk-queue').addEventListener('click', bulkQueueSelected);
  document.getElementById('btn-bulk-delete').addEventListener('click', bulkDeleteSelected);

  document.getElementById('clear-queue').addEventListener('click', () => {
    if(confirm('Are you sure you want to clear the print queue?')) {
      printQueue = [];
      savePrintQueueToStorage();
      renderPrintQueue();
      updateBadges();
    }
  });
  document.getElementById('trigger-batch-print').addEventListener('click', printQueueA4Layout);

  const pdfInput = document.getElementById('pdf-upload');
  const pdfZone = document.getElementById('pdf-upload-zone');
  
  if (pdfInput && pdfZone) {
    pdfInput.addEventListener('change', handlePdfFileSelect);
    
    pdfZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      pdfZone.closest('.pdf-upload-container').classList.add('dragover');
    });
    
    pdfZone.addEventListener('dragleave', () => {
      pdfZone.closest('.pdf-upload-container').classList.remove('dragover');
    });
    
    pdfZone.addEventListener('drop', (e) => {
      e.preventDefault();
      pdfZone.closest('.pdf-upload-container').classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        pdfInput.files = e.dataTransfer.files;
        handlePdfFileSelect();
      }
    });
  }

  const designSelect = document.getElementById('design-select');
  if (designSelect) {
    const savedDesign = localStorage.getItem('ration_card_design') || '1';
    designSelect.value = savedDesign;
    selectedDesign = savedDesign;
    setTimeout(() => { applyCardDesign(savedDesign); }, 100);

    designSelect.addEventListener('change', (e) => {
      const design = e.target.value;
      selectedDesign = design;
      localStorage.setItem('ration_card_design', design);
      applyCardDesign(design);
    });
  }
}

function applyCardDesign(design) {
  const frontCard = document.getElementById('live-card-front');
  const backCard = document.getElementById('live-card-back');
  if (frontCard && backCard) {
    frontCard.classList.remove('design-1-front', 'design-2-front', 'design-3-front');
    backCard.classList.remove('design-1-back', 'design-2-back', 'design-3-back');
    
    frontCard.classList.add(`design-${design}-front`);
    backCard.classList.add(`design-${design}-back`);
  }
}

/* ==========================================================================
   TABS MANAGEMENT
   ========================================================================== */
function switchTab(tabId) {
  const navButtons = document.querySelectorAll('.nav-btn');
  navButtons.forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  const tabs = document.querySelectorAll('.tab-content');
  tabs.forEach(tab => {
    if (tab.id === `${tabId}-tab`) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  if (tabId === 'history') {
    loadHistory();
  } else if (tabId === 'print-queue') {
    renderPrintQueue();
  }

  if (typeof resizeIdCards === 'function') {
    setTimeout(resizeIdCards, 50);
  }
}

function updateBadges() {
  document.getElementById('history-count').innerText = historyCards.length;
  document.getElementById('queue-count').innerText = printQueue.length;
  
  const selectedCount = document.querySelectorAll('.record-checkbox:checked').length;
  document.getElementById('selected-count').innerText = selectedCount;
}

/* ==========================================================================
   FORM & FAMILY MEMBERS CONTROLLER
   ========================================================================== */
function resetForm() {
  currentEditingId = null;
  document.getElementById('ration-form').reset();
  removeUploadedPhoto();
  
  // Reset design to default
  const designSelect = document.getElementById('design-select');
  if (designSelect) designSelect.value = '1';
  selectedDesign = '1';
  applyCardDesign('1');

  const tableBody = document.querySelector('#family-table tbody');
  tableBody.innerHTML = '';
  addFamilyTableRow('1', 'Babu Jalela', '30', 'F', 'SELF', 'XXXX-XXXX-3401');

  updateLivePreview();
}

function addFamilyTableRow(sr = '', name = '', age = '', gender = 'F', relation = '', aadhaar = '') {
  const tableBody = document.querySelector('#family-table tbody');
  const rowId = 'row_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
  const rowsCount = tableBody.querySelectorAll('tr').length + 1;
  const finalSr = sr || rowsCount.toString();
  
  const tr = document.createElement('tr');
  tr.id = rowId;
  tr.innerHTML = `
    <td><input type="text" class="input-sr" style="text-align: center;" value="${finalSr}" required></td>
    <td><input type="text" class="input-name" placeholder="Member Name" value="${name}" required></td>
    <td><input type="number" class="input-age" placeholder="Age" value="${age}" required></td>
    <td>
      <select class="input-gender" required>
        <option value="F" ${gender === 'F' ? 'selected' : ''}>F</option>
        <option value="M" ${gender === 'M' ? 'selected' : ''}>M</option>
      </select>
    </td>
    <td><input type="text" class="input-relation" placeholder="Relation" value="${relation}" required></td>
    <td><input type="text" class="input-aadhaar" placeholder="Aadhaar Number" value="${aadhaar}" required></td>
    <td>
      <button type="button" class="btn btn-danger btn-sm btn-icon delete-row-btn" title="Remove Row">
        <i data-lucide="minus"></i>
      </button>
    </td>
  `;
  
  const inputs = tr.querySelectorAll('input, select');
  inputs.forEach(inp => {
    inp.addEventListener('input', updateLivePreview);
    inp.addEventListener('change', updateLivePreview);
  });

  tr.querySelector('.delete-row-btn').addEventListener('click', () => {
    tr.remove();
    updateLivePreview();
  });

  tableBody.appendChild(tr);
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: 'lucide' } });
  }
  updateLivePreview();
}

function getFamilyTableData() {
  const data = [];
  const rows = document.querySelectorAll('#family-table tbody tr');
  rows.forEach(row => {
    data.push({
      sr: row.querySelector('.input-sr').value,
      name: row.querySelector('.input-name').value.trim(),
      age: row.querySelector('.input-age').value,
      gender: row.querySelector('.input-gender').value,
      relation: row.querySelector('.input-relation').value.trim(),
      aadhaar: row.querySelector('.input-aadhaar').value.trim()
    });
  });
  return data;
}

/* ==========================================================================
   PHOTO UPLOAD OPERATIONS
   ========================================================================== */
function handlePhotoSelection() {
  const fileInput = document.getElementById('photo-upload');
  const previewImg = document.getElementById('photo-preview-img');
  const uploadPlaceholder = document.querySelector('.upload-placeholder');
  const removeBtn = document.querySelector('.remove-photo-btn');
  
  if (fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const maxDim = 300;
        let w = img.width;
        let h = img.height;
        if (w > h) {
          if (w > maxDim) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          }
        } else {
          if (h > maxDim) {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        
        const base64Photo = canvas.toDataURL('image/jpeg', 0.85);
        
        previewImg.src = base64Photo;
        previewImg.classList.remove('hidden');
        uploadPlaceholder.classList.add('hidden');
        removeBtn.classList.remove('hidden');
        
        document.getElementById('card-photo').src = base64Photo;
        const d3Photo = document.getElementById('d3-card-photo');
        if (d3Photo) d3Photo.src = base64Photo;
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }
}

function removeUploadedPhoto() {
  document.getElementById('photo-upload').value = '';
  
  const previewImg = document.getElementById('photo-preview-img');
  const uploadPlaceholder = document.querySelector('.upload-placeholder');
  const removeBtn = document.querySelector('.remove-photo-btn');
  
  previewImg.src = '';
  previewImg.classList.add('hidden');
  uploadPlaceholder.classList.remove('hidden');
  removeBtn.classList.add('hidden');
  
  document.getElementById('card-photo').src = placeholderAvatar;
  const d3Photo = document.getElementById('d3-card-photo');
  if (d3Photo) d3Photo.src = placeholderAvatar;
}

/* ==========================================================================
   LIVE CARD PREVIEW CONTROLLER & QR ENGINE
   ========================================================================== */
let qrCodeGenerator = null;

function updateLivePreview() {
  const cardNo = document.getElementById('ration-card-number').value || '218541384974';
  const scheme = document.getElementById('scheme-name').value || 'PHH';
  const head = document.getElementById('head-of-family').value || 'Babu Jalela';
  
  // Format Issue Date from YYYY-MM-DD to DD/MM/YYYY
  const issueInput = document.getElementById('issue-date').value;
  let formattedIssue = '23/05/2019';
  if (issueInput) {
    if (issueInput.includes('-')) {
      const parts = issueInput.split('-');
      if (parts.length === 3) {
        formattedIssue = `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
    } else {
      formattedIssue = issueInput;
    }
  }
  
  const fps = document.getElementById('fare-shop-number').value || '203453344';
  const mobile = document.getElementById('mobile-number').value || '1234567890';
  const address = document.getElementById('address').value || 'Uganada Ki kali ghati, ki kali gufa number 2';

  // Update front (Classic)
  const cardPill = document.getElementById('card-number-pill');
  if (cardPill) cardPill.innerText = cardNo;
  const cardGrid = document.getElementById('card-number-grid');
  if (cardGrid) cardGrid.innerText = cardNo;
  
  document.getElementById('card-scheme').innerText = scheme;
  document.getElementById('card-head').innerText = head;
  document.getElementById('card-fps').innerText = fps;
  document.getElementById('card-mobile').innerText = mobile;
  document.getElementById('card-issue').innerText = formattedIssue;

  // Update front (Design 3)
  const d3Fps = document.getElementById('d3-card-fps');
  if (d3Fps) d3Fps.innerText = fps;
  const d3Scheme = document.getElementById('d3-card-scheme');
  if (d3Scheme) d3Scheme.innerText = scheme;
  const d3Head = document.getElementById('d3-card-head');
  if (d3Head) d3Head.innerText = head;
  const d3Address = document.getElementById('d3-card-address');
  if (d3Address) d3Address.innerText = address;
  const d3Mobile = document.getElementById('d3-card-mobile');
  if (d3Mobile) d3Mobile.innerText = mobile;
  const d3Issue = document.getElementById('d3-card-issue');
  if (d3Issue) d3Issue.innerText = formattedIssue;
  const d3CardNo = document.getElementById('d3-card-number-val');
  if (d3CardNo) d3CardNo.innerText = cardNo;
  
  const photoPreview = document.getElementById('photo-preview-img');
  const photoSrc = (photoPreview && !photoPreview.classList.contains('hidden')) ? photoPreview.src : placeholderAvatar;
  const d3Photo = document.getElementById('d3-card-photo');
  if (d3Photo) d3Photo.src = photoSrc;

  // Update back
  document.getElementById('card-back-card-number').innerText = cardNo;
  document.getElementById('card-back-address').innerText = address;

  // Update family members table
  const familyData = getFamilyTableData();
  const cardTableBody = document.querySelector('#card-members-table tbody');
  const d3CardTableBody = document.querySelector('#d3-card-members-table tbody');
  
  if (cardTableBody) cardTableBody.innerHTML = '';
  if (d3CardTableBody) d3CardTableBody.innerHTML = '';
  
  // Show up to 5 rows in preview card to fit dimension height constraints for Designs 1 & 2
  const previewRows = familyData.slice(0, 5);
  
  if (previewRows.length === 0) {
    if (cardTableBody) cardTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #aaa;">No members added</td></tr>`;
  } else {
    previewRows.forEach(row => {
      if (cardTableBody) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.sr || '-'}</td>
          <td style="font-weight: 700;">${row.name || '-'}</td>
          <td>${row.age || '-'}</td>
          <td>${row.gender || '-'}</td>
          <td>${row.relation || '-'}</td>
          <td style="font-family: monospace;">${row.aadhaar || '-'}</td>
        `;
        cardTableBody.appendChild(tr);
      }
    });
  }

  // Populate Design 3 table with all family members (card height will stretch)
  if (familyData.length === 0) {
    if (d3CardTableBody) d3CardTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #aaa;">No members added</td></tr>`;
  } else {
    familyData.forEach(row => {
      if (d3CardTableBody) {
        const trD3 = document.createElement('tr');
        const ageGender = (row.age || '-') + ' / ' + (row.gender || '-').toUpperCase();
        trD3.innerHTML = `
          <td>${row.sr || '-'}</td>
          <td style="font-weight: 700;">${row.name || '-'}</td>
          <td>${ageGender}</td>
          <td>${row.relation || '-'}</td>
          <td>${row.aadhaar || '-'}</td>
        `;
        d3CardTableBody.appendChild(trD3);
      }
    });
  }

  // QR Code
  let qrString = `Ration Card: ${cardNo}\nHead of Family: ${head}\nMobile: ${mobile}\nFamily Members: ${familyData.length}`;
  const qrTarget = document.getElementById('card-qr');
  qrTarget.innerHTML = '';
  
  qrCodeGenerator = new QRCode(qrTarget, {
    text: qrString,
    width: 75,
    height: 75,
    colorDark: "#1a237e",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.M
  });
}

/* ==========================================================================
   CRUD OPERATIONS
   ========================================================================== */
async function handleFormSubmit(e) {
  e.preventDefault();

  const cardNumber = document.getElementById('ration-card-number').value;
  const schemeName = document.getElementById('scheme-name').value;
  const headOfFamily = document.getElementById('head-of-family').value;
  const issueInput = document.getElementById('issue-date').value;
  let issueDate = issueInput;
  if (issueInput && issueInput.includes('-')) {
    const parts = issueInput.split('-');
    if (parts.length === 3) {
      issueDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
  }
  const fareShopNumber = document.getElementById('fare-shop-number').value;
  const mobile = document.getElementById('mobile-number').value;
  const address = document.getElementById('address').value;
  
  const photoPreview = document.getElementById('photo-preview-img');
  const photoBase64 = photoPreview.classList.contains('hidden') ? placeholderAvatar : photoPreview.src;
  const familyMembers = getFamilyTableData();

  const cardData = {
    cardNumber,
    schemeName,
    headOfFamily,
    issueDate,
    fareShopNumber,
    mobile,
    address,
    photo: photoBase64,
    familyMembers,
    designStyle: selectedDesign,
    createdAt: Date.now()
  };

  const isEditing = currentEditingId !== null;
  if (isEditing) {
    cardData.id = currentEditingId;
  }

  const saveBtn = document.querySelector('#ration-form button[type="submit"]');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = isEditing ? '<i data-lucide="loader"></i> Saving...' : '<i data-lucide="loader"></i> Charging & Saving...';
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  try {
    await saveCard(cardData);
    alert(isEditing ? 'Ration Card updated successfully!' : 'Ration Card saved! 50 Coins deducted.');
    resetForm();
    await loadHistory();
    switchTab('history');
  } catch (err) {
    console.error('Error saving record:', err);
    alert('Failed to save record: ' + err.message);
    if (err.isInsufficientBalance) {
      window.location.href = err.redirectUrl || '/wallet/topup/';
    }
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i data-lucide="save"></i> Save Ration Card';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }
}

async function loadHistory() {
  try {
    const list = await getAllCards();
    historyCards = list.sort((a, b) => b.createdAt - a.createdAt); 
    renderHistoryList(historyCards);
    updateBadges();
  } catch (err) {
    console.error('Error loading history:', err);
  }
}

function renderHistoryList(records) {
  const tbody = document.getElementById('history-list-body');
  tbody.innerHTML = '';

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-folder-open"><path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/></svg>
          <p>No records found in database. Create your first card!</p>
        </td>
      </tr>
    `;
    return;
  }

  records.forEach(card => {
    const printCount  = card.printCount || 0;
    const freePrints  = 2;
    const remaining   = Math.max(0, freePrints - printCount);
    const printBadgeColor = remaining > 0 ? '#22c55e' : '#ef4444';
    const printBadgeBg    = remaining > 0 ? '#dcfce7' : '#fee2e2';
    const printBadgeTip   = remaining > 0
      ? `${remaining} free print${remaining === 1 ? '' : 's'} remaining`
      : `Free prints used — next print costs 50 Coins`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <input type="checkbox" class="record-checkbox" data-id="${card.id}">
      </td>
      <td>
        <img class="table-member-photo" src="${card.photo || placeholderAvatar}" alt="Photo">
      </td>
      <td style="font-family: monospace; font-weight: bold;">${card.cardNumber}</td>
      <td>
        <div class="farmer-table-name" style="font-weight: bold; color: var(--primary-color);">${card.headOfFamily}</div>
        <div style="font-size:0.75rem; color:#666;">${card.address}</div>
      </td>
      <td><span class="badge" style="background:#e8eaf6; color:var(--primary-color); font-weight:bold; border-radius:4px; padding:2px 6px;">${card.schemeName}</span></td>
      <td>${card.mobile}</td>
      <td style="text-align: center;">
        <span class="badge" style="background-color: var(--light-sage); color: var(--primary-color); font-weight: bold; border-radius: 4px;">
          ${card.familyMembers ? card.familyMembers.length : 0}
        </span>
      </td>
      <td style="text-align: center;">
        <span title="${printBadgeTip}" style="display:inline-flex;align-items:center;gap:3px;font-size:0.75rem;font-weight:700;padding:2px 7px;border-radius:20px;background:${printBadgeBg};color:${printBadgeColor};border:1px solid ${printBadgeColor}40;cursor:default;">
          🖨️ ${remaining > 0 ? remaining + ' left' : 'Paid'}
        </span>
      </td>
      <td>
        <div class="table-actions">
          <button class="btn btn-secondary btn-sm btn-icon edit-card-btn" data-id="${card.id}" title="Edit Card Details">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-edit-3"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          </button>
          <button class="btn btn-secondary btn-sm btn-icon queue-card-btn" data-id="${card.id}" title="Add to Print Queue">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-plus"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M12 12v6"/></svg>
          </button>
          <button class="btn btn-danger btn-sm btn-icon delete-card-btn" data-id="${card.id}" title="Delete Record">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
          </button>
        </div>
      </td>
    `;

    tr.querySelector('.edit-card-btn').addEventListener('click', () => editCard(card.id));
    tr.querySelector('.queue-card-btn').addEventListener('click', () => queueSingleCard(card));
    tr.querySelector('.delete-card-btn').addEventListener('click', () => deleteCardConfirm(card.id));
    
    tr.querySelector('.record-checkbox').addEventListener('change', () => {
      updateBadges();
    });

    tbody.appendChild(tr);
  });
}

function filterHistoryList() {
  const query = document.getElementById('history-search').value.toLowerCase().trim();
  if(!query) {
    renderHistoryList(historyCards);
    return;
  }
  
  const filtered = historyCards.filter(c => {
    return c.cardNumber.toLowerCase().includes(query) || 
           c.headOfFamily.toLowerCase().includes(query) || 
           c.address.toLowerCase().includes(query) ||
           (c.familyMembers && c.familyMembers.some(m => m.name.toLowerCase().includes(query) || m.aadhaar.includes(query)));
  });
  renderHistoryList(filtered);
}

function toggleAllRecordsSelection() {
  const state = document.getElementById('select-all-records').checked;
  const checkboxes = document.querySelectorAll('.record-checkbox');
  checkboxes.forEach(cb => cb.checked = state);
  updateBadges();
}

function bulkQueueSelected() {
  const selectedCheckboxes = document.querySelectorAll('.record-checkbox:checked');
  if (selectedCheckboxes.length === 0) {
    alert('Please select at least one record to queue.');
    return;
  }
  
  let added = 0;
  selectedCheckboxes.forEach(cb => {
    const id = parseInt(cb.getAttribute('data-id'));
    const card = historyCards.find(c => c.id === id);
    if (card) {
      const alreadyInQueue = printQueue.some(q => q.id === card.id);
      if(!alreadyInQueue) {
        printQueue.push(card);
        added++;
      }
    }
  });
  
  if (added > 0) {
    savePrintQueueToStorage();
    alert(`Added ${added} cards to print queue.`);
  } else {
    alert('Selected card(s) are already in the print queue.');
  }
  
  // Uncheck all
  document.getElementById('select-all-records').checked = false;
  selectedCheckboxes.forEach(cb => cb.checked = false);
  updateBadges();
}

function bulkDeleteSelected() {
  const selectedCheckboxes = document.querySelectorAll('.record-checkbox:checked');
  if (selectedCheckboxes.length === 0) {
    alert('Please select at least one record to delete.');
    return;
  }
  
  if(!confirm(`Are you sure you want to permanently delete the ${selectedCheckboxes.length} selected records?`)) {
    return;
  }
  
  const promises = [];
  selectedCheckboxes.forEach(cb => {
    const id = parseInt(cb.getAttribute('data-id'));
    promises.push(deleteCardFromDB(id));
  });
  
  Promise.all(promises)
    .then(() => {
      alert('Selected records deleted successfully.');
      return loadHistory();
    })
    .catch(err => {
      console.error(err);
      alert('Error during deletion: ' + err.message);
      loadHistory();
    });
}

async function editCard(id) {
  try {
    const card = await getCardById(id);
    if (!card) {
      alert('Card details could not be found.');
      return;
    }
    
    currentEditingId = card.id;
    switchTab('creator');
    
    // Load saved design
    const designVal = card.designStyle || '1';
    selectedDesign = designVal;
    const designSelect = document.getElementById('design-select');
    if (designSelect) designSelect.value = designVal;
    applyCardDesign(designVal);
    
    // Fill Form Inputs
    document.getElementById('ration-card-number').value = card.cardNumber;
    document.getElementById('scheme-name').value = card.schemeName;
    document.getElementById('head-of-family').value = card.headOfFamily;
    
    // Populate Issue Date into date picker
    let dbIssueDate = card.issueDate || "";
    let formIssueDate = "";
    if (dbIssueDate.includes('/')) {
      const parts = dbIssueDate.split('/');
      if (parts.length === 3) {
        formIssueDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
    } else {
      formIssueDate = dbIssueDate;
    }
    document.getElementById('issue-date').value = formIssueDate;
    
    document.getElementById('fare-shop-number').value = card.fareShopNumber;
    document.getElementById('mobile-number').value = card.mobile;
    document.getElementById('address').value = card.address;
    
    // Photo Preview
    const previewImg = document.getElementById('photo-preview-img');
    const uploadPlaceholder = document.querySelector('.upload-placeholder');
    const removeBtn = document.querySelector('.remove-photo-btn');
    
    if (card.photo && card.photo !== placeholderAvatar) {
      previewImg.src = card.photo;
      previewImg.classList.remove('hidden');
      uploadPlaceholder.classList.add('hidden');
      removeBtn.classList.remove('hidden');
      document.getElementById('card-photo').src = card.photo;
      const d3Photo = document.getElementById('d3-card-photo');
      if (d3Photo) d3Photo.src = card.photo;
    } else {
      removeUploadedPhoto();
    }
    
    // Family members table
    const tableBody = document.querySelector('#family-table tbody');
    tableBody.innerHTML = '';
    if (card.familyMembers && card.familyMembers.length > 0) {
      card.familyMembers.forEach(member => {
        addFamilyTableRow(member.sr, member.name, member.age, member.gender, member.relation, member.aadhaar);
      });
    } else {
      addFamilyTableRow();
    }
    
    updateLivePreview();
  } catch (error) {
    console.error('Error loading card for edit:', error);
    alert('Failed to edit card.');
  }
}

function queueSingleCard(card) {
  const alreadyInQueue = printQueue.some(q => q.id === card.id);
  if (alreadyInQueue) {
    alert('This card is already in the print queue.');
    return;
  }
  
  printQueue.push(card);
  savePrintQueueToStorage();
  updateBadges();
  alert('Added card to print queue!');
}

function deleteCardConfirm(id) {
  if (confirm('Are you sure you want to permanently delete this ration card record?')) {
    deleteCardFromDB(id)
      .then(() => {
        alert('Record deleted successfully.');
        loadHistory();
      })
      .catch(err => {
        alert('Failed to delete: ' + err.message);
      });
  }
}

/* ==========================================================================
   PRINT QUEUE STORAGE & RENDERING
   ========================================================================== */
function savePrintQueueToStorage() {
  localStorage.setItem('ration_print_queue', JSON.stringify(printQueue));
}

function loadPrintQueueFromStorage() {
  const stored = localStorage.getItem('ration_print_queue');
  if(stored) {
    try {
      printQueue = JSON.parse(stored);
    } catch (e) {
      printQueue = [];
    }
  }
  updateBadges();
}

function renderPrintQueue() {
  const qGrid = document.getElementById('queue-grid-list');
  qGrid.innerHTML = '';

  if (printQueue.length === 0) {
    qGrid.innerHTML = `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layers"><path d="m12 3-10 5L12 13l10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
        <p>Your print queue is empty. Add cards from history or the creator to print.</p>
      </div>
    `;
    return;
  }

  printQueue.forEach((card, index) => {
    const row = document.createElement('div');
    row.className = 'queue-row-card';
    row.innerHTML = `
      <div class="queue-card-preview-mini">
        <!-- Front side preview -->
        <div class="id-card-wrapper">
          <div class="id-card card-front design-${card.designStyle || '1'}-front">
            <!-- Classic Front Layout (Designs 1 & 2) -->
            <div class="classic-layout-front">
              <!-- Logo -->
              <img src="/static/id_cards/ration-card/logo.png" class="logo-ration"/>
              <div class="card-body">
                <div class="photo-container">
                  <img src="${card.photo || placeholderAvatar}">
                </div>
                <div class="card-details">
                  <div class="detail-grid">
                    <div id="card-number-grid-row" style="display: contents;">
                      <div class="detail-label">Card No:</div>
                      <div class="detail-val" id="card-number-grid">${card.cardNumber}</div>
                    </div>
                    <div class="detail-label">Head Of Family:</div>
                    <div class="detail-val">${card.headOfFamily}</div>
                    <div class="detail-label">Scheme:</div>
                    <div class="detail-val">${card.schemeName}</div>
                    <div class="detail-label">FPS No:</div>
                    <div class="detail-val">${card.fareShopNumber}</div>
                    <div class="detail-label">Mobile:</div>
                    <div class="detail-val">${card.mobile}</div>
                    <div class="detail-label">Issue:</div>
                    <div class="detail-val">${card.issueDate}</div>
                  </div>
                </div>
                <div class="qr-container">
                  <div class="mini-qr-${card.id || index}"></div>
                </div>
              </div>
              <!-- Ration Card Pill Badge -->
              <div class="id-badge-container" id="card-number-pill-container">
                <div class="ration-id-badge">
                  Ration Card No: <span id="card-number-pill">${card.cardNumber}</span>
                </div>
              </div>
            </div>

            <!-- Design 3 Front Layout -->
            <div class="design3-layout-front">
              <!-- Title & Shop No at top -->
              <div class="d3-title-block">
                <div class="d3-title-text">Ration Card</div>
                <div class="d3-shop-no">Fare Price Shop No: <span>${card.fareShopNumber}</span></div>
              </div>
              
              <!-- Content section -->
              <div class="d3-content-section">
                <!-- Left column: Photo and Issue Date -->
                <div class="d3-photo-col">
                  <div class="d3-photo-container">
                    <img src="${card.photo || placeholderAvatar}">
                  </div>
                  <div class="d3-issue-block">
                    <div class="d3-issue-label">Issue Date</div>
                    <div class="d3-issue-val">${card.issueDate}</div>
                  </div>
                </div>
                
                <!-- Right column: Details grid -->
                <div class="d3-details-col">
                  <div class="d3-detail-row">
                    <span class="d3-label">Scheme Name:</span>
                    <span class="d3-val">${card.schemeName}</span>
                  </div>
                  <div class="d3-detail-row">
                    <span class="d3-label">Head of Family:</span>
                    <span class="d3-val">${card.headOfFamily}</span>
                  </div>
                  <div class="d3-detail-row">
                    <span class="d3-label">Address:</span>
                    <span class="d3-val d3-address">${card.address}</span>
                  </div>
                  <div class="d3-detail-row">
                    <span class="d3-label">Mobile Number:</span>
                    <span class="d3-val">${card.mobile}</span>
                  </div>
                </div>
              </div>
              
              <!-- Footer block -->
              <div class="d3-footer-block">
                <div class="d3-sig-placeholder"></div>
                <div class="d3-number-block">
                  <div class="d3-number-label">Ration Card Number</div>
                  <div class="d3-number-val">${card.cardNumber}</div>
                </div>
                <div class="d3-sig-placeholder"></div>
              </div>
              <div class="d3-footer-email">up.fncs@gmail.com</div>
            </div>
          </div>
        </div>

        <!-- Back side preview -->
        <div class="id-card-wrapper">
          <div class="id-card card-back design-${card.designStyle || '1'}-back">
            <!-- Classic Back Layout (Designs 1 & 2) -->
            <div class="classic-layout-back">
              <div class="card-back-body">
                <div class="back-header-row">
                  <div class="back-title">Family Details</div>
                  <div class="back-card-no">${card.cardNumber}</div>
                </div>
                <div class="address-container">
                  <strong>Address:</strong> <span>${card.address}</span>
                </div>
                <div class="members-table-container">
                  <table class="card-members-table">
                    <thead>
                      <tr>
                        <th style="width: 25px;">S.R.</th>
                        <th>Member Name</th>
                        <th style="width: 30px;">Age</th>
                        <th style="width: 30px;">Gnd</th>
                        <th style="width: 55px;">Relation</th>
                        <th>Aadhaar No.</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${(card.familyMembers || []).slice(0, 5).map(m => `
                        <tr>
                          <td>${m.sr}</td>
                          <td style="font-weight: 700;">${m.name}</td>
                          <td>${m.age}</td>
                          <td>${m.gender}</td>
                          <td>${m.relation}</td>
                          <td style="font-family: monospace;">${m.aadhaar}</td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Design 3 Back Layout -->
            <div class="design3-layout-back">
              <div class="d3-back-header">
                <img src="/static/id_cards/ration-card/design 3 back header.png" alt="Header">
              </div>
              <div class="d3-back-content">
                <table class="d3-members-table">
                  <thead>
                    <tr>
                      <th style="width: 5%;">Sr</th>
                      <th style="width: 32%;">Member Name</th>
                      <th style="width: 15%;">Age/Gender</th>
                      <th style="width: 20%;">Relation</th>
                      <th style="width: 28%;">Aadhar No.</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${(card.familyMembers || []).map(m => `
                      <tr>
                        <td>${m.sr}</td>
                        <td style="font-weight: 700;">${m.name}</td>
                        <td>${m.age} / ${m.gender.toUpperCase()}</td>
                        <td>${m.relation}</td>
                        <td>${m.aadhaar}</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
              <div class="d3-back-footer">
                <img src="/static/id_cards/ration-card/design 3 back footer.png" alt="Footer">
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="queue-card-info">
        <h4>${card.headOfFamily}</h4>
        <p>Card Number: <strong>${card.cardNumber}</strong> | Scheme: ${card.schemeName}</p>
        <p>Family Members: ${card.familyMembers ? card.familyMembers.length : 0}</p>
      </div>
      
      <button class="btn btn-danger btn-sm remove-queue-btn" data-index="${index}">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg> Remove
      </button>
    `;

    row.querySelector('.remove-queue-btn').addEventListener('click', () => {
      printQueue.splice(index, 1);
      savePrintQueueToStorage();
      renderPrintQueue();
      updateBadges();
    });

    qGrid.appendChild(row);

    // Initialize mini QR
    setTimeout(() => {
      const qrEl = row.querySelector(`.mini-qr-${card.id || index}`);
      if(qrEl) {
        let qrString = `Ration Card: ${card.cardNumber}\nHead of Family: ${card.headOfFamily}\nMobile: ${card.mobile}\nFamily Members: ${card.familyMembers ? card.familyMembers.length : 0}`;
        new QRCode(qrEl, {
          text: qrString,
          width: 50,
          height: 50,
          colorDark: "#1a237e",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    }, 50);
  });
}

/* ==========================================================================
   A4 PRINT COMPILER
   ========================================================================== */
async function printQueueA4Layout() {
  if (printQueue.length === 0) {
    alert('Print queue is empty. Please add cards from your history database first.');
    return;
  }

  // Double check user balance
  const quantity = printQueue.length;
  let chargeNeeded = 0;
  const cardsToCharge = [];

  for (let card of printQueue) {
    if (card.id) {
      const fresh = await getCardById(card.id);
      const currentCount = fresh ? (fresh.printCount || 0) : 0;
      if (currentCount >= 2) {
        chargeNeeded++;
        cardsToCharge.push(card);
      }
    }
  }

  const totalCost = chargeNeeded * window.RATION_PRICE;
  if (chargeNeeded > 0) {
    if (window.WALLET_BALANCE < totalCost) {
      alert(`Insufficient balance. You need ${totalCost} Coins to print the queued cards. Your balance is ${window.WALLET_BALANCE} Coins.`);
      window.location.href = '/wallet/topup/';
      return;
    }
    if (!confirm(`This operation will print ${quantity} card(s). ${chargeNeeded} card(s) have already used their 2 free prints. This will deduct ${totalCost} Coins from your wallet. Proceed?`)) {
      return;
    }
  }

  // Deduct coins first inside try-catch loop
  try {
    for (let card of cardsToCharge) {
      await processPrintCharge(card);
    }
  } catch (err) {
    console.error('Wallet charge deduction failed before print compiler:', err);
    alert('Deduction failed: ' + err.message + '\nPrint operation cancelled.');
    if (err.isInsufficientBalance) {
      window.location.href = err.redirectUrl || '/wallet/topup/';
    }
    return;
  }

  const printContainer = document.getElementById('print-container');
  printContainer.innerHTML = '';

  const cardsPerPageSelect = document.getElementById('cards-per-page');
  const cardsPerPage = parseInt(cardsPerPageSelect ? cardsPerPageSelect.value : 3);

  // Group cards by page
  let currentPageDiv = null;
  printQueue.forEach((card, idx) => {
    if (idx % cardsPerPage === 0) {
      currentPageDiv = document.createElement('div');
      currentPageDiv.className = 'print-page';
      printContainer.appendChild(currentPageDiv);
    }

    const row = document.createElement('div');
    row.className = 'print-row-item';
    row.innerHTML = `
      <!-- Front side scaled for A4 print -->
      <div class="print-card-scaler">
        <div class="id-card card-front design-${card.designStyle || '1'}-front">
          <!-- Classic Front Layout (Designs 1 & 2) -->
          <div class="classic-layout-front">
            <!-- Logo -->
            <img src="/static/id_cards/ration-card/logo.png" class="logo-ration"/>
            <div class="card-body">
              <div class="photo-container">
                <img src="${card.photo || placeholderAvatar}">
              </div>
              <div class="card-details">
                <div class="detail-grid">
                  <div id="card-number-grid-row" style="display: contents;">
                    <div class="detail-label">Card No:</div>
                    <div class="detail-val" id="card-number-grid">${card.cardNumber}</div>
                  </div>
                  <div class="detail-label">Head Of Family:</div>
                  <div class="detail-val">${card.headOfFamily}</div>
                  <div class="detail-label">Scheme:</div>
                  <div class="detail-val">${card.schemeName}</div>
                  <div class="detail-label">FPS No:</div>
                  <div class="detail-val">${card.fareShopNumber}</div>
                  <div class="detail-label">Mobile:</div>
                  <div class="detail-val">${card.mobile}</div>
                  <div class="detail-label">Issue:</div>
                  <div class="detail-val">${card.issueDate}</div>
                </div>
              </div>
              <div class="qr-container">
                <div class="print-qr-${card.id || idx}"></div>
              </div>
            </div>
            <!-- Ration Card Pill Badge -->
            <div class="id-badge-container" id="card-number-pill-container">
              <div class="ration-id-badge">
                Ration Card No: <span id="card-number-pill">${card.cardNumber}</span>
              </div>
            </div>
          </div>

          <!-- Design 3 Front Layout -->
          <div class="design3-layout-front">
            <!-- Title & Shop No at top -->
            <div class="d3-title-block">
              <div class="d3-title-text">Ration Card</div>
              <div class="d3-shop-no">Fare Price Shop No: <span>${card.fareShopNumber}</span></div>
            </div>
            
            <!-- Content section -->
            <div class="d3-content-section">
              <!-- Left column: Photo and Issue Date -->
              <div class="d3-photo-col">
                <div class="d3-photo-container">
                  <img src="${card.photo || placeholderAvatar}">
                </div>
                <div class="d3-issue-block">
                  <div class="d3-issue-label">Issue Date</div>
                  <div class="d3-issue-val">${card.issueDate}</div>
                </div>
              </div>
              
              <!-- Right column: Details grid -->
              <div class="d3-details-col">
                <div class="d3-detail-row">
                  <span class="d3-label">Scheme Name:</span>
                  <span class="d3-val">${card.schemeName}</span>
                </div>
                <div class="d3-detail-row">
                  <span class="d3-label">Head of Family:</span>
                  <span class="d3-val">${card.headOfFamily}</span>
                </div>
                <div class="d3-detail-row">
                  <span class="d3-label">Address:</span>
                  <span class="d3-val d3-address">${card.address}</span>
                </div>
                <div class="d3-detail-row">
                  <span class="d3-label">Mobile Number:</span>
                  <span class="d3-val">${card.mobile}</span>
                </div>
              </div>
            </div>
            
            <!-- Footer block -->
            <div class="d3-footer-block">
              <div class="d3-sig-placeholder"></div>
              <div class="d3-number-block">
                <div class="d3-number-label">Ration Card Number</div>
                <div class="d3-number-val">${card.cardNumber}</div>
              </div>
              <div class="d3-sig-placeholder"></div>
            </div>
            <div class="d3-footer-email">up.fncs@gmail.com</div>
          </div>
        </div>
      </div>

      <!-- Back side scaled for A4 print -->
      <div class="print-card-scaler">
        <div class="id-card card-back design-${card.designStyle || '1'}-back">
          <!-- Classic Back Layout (Designs 1 & 2) -->
          <div class="classic-layout-back">
            <div class="card-back-body">
              <div class="back-header-row">
                <div class="back-title">Family Details</div>
                <div class="back-card-no">${card.cardNumber}</div>
              </div>
              <div class="address-container">
                <strong>Address:</strong> <span>${card.address}</span>
              </div>
              <div class="members-table-container">
                <table class="card-members-table">
                  <thead>
                    <tr>
                      <th style="width: 25px;">S.R.</th>
                      <th>Member Name</th>
                      <th style="width: 30px;">Age</th>
                      <th style="width: 30px;">Gnd</th>
                      <th style="width: 55px;">Relation</th>
                      <th>Aadhaar No.</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${(card.familyMembers || []).slice(0, 5).map(m => `
                      <tr>
                        <td>${m.sr}</td>
                        <td style="font-weight: 700;">${m.name}</td>
                        <td>${m.age}</td>
                        <td>${m.gender}</td>
                        <td>${m.relation}</td>
                        <td style="font-family: monospace;">${m.aadhaar}</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Design 3 Back Layout -->
          <div class="design3-layout-back">
            <div class="d3-back-header">
              <img src="/static/id_cards/ration-card/design 3 back header.png" alt="Header">
            </div>
            <div class="d3-back-content">
              <table class="d3-members-table">
                <thead>
                  <tr>
                    <th style="width: 5%;">Sr</th>
                    <th style="width: 32%;">Member Name</th>
                    <th style="width: 15%;">Age/Gender</th>
                    <th style="width: 20%;">Relation</th>
                    <th style="width: 28%;">Aadhar No.</th>
                  </tr>
                </thead>
                <tbody>
                  ${(card.familyMembers || []).map(m => `
                    <tr>
                      <td>${m.sr}</td>
                      <td style="font-weight: 700;">${m.name}</td>
                      <td>${m.age} / ${m.gender.toUpperCase()}</td>
                      <td>${m.relation}</td>
                      <td>${m.aadhaar}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            <div class="d3-back-footer">
              <img src="/static/id_cards/ration-card/design 3 back footer.png" alt="Footer">
            </div>
          </div>
        </div>
      </div>
    `;

    currentPageDiv.appendChild(row);

    // Initialize print QR
    setTimeout(() => {
      const qrEl = row.querySelector(`.print-qr-${card.id || idx}`);
      if(qrEl) {
        let qrString = `Ration Card: ${card.cardNumber}\nHead of Family: ${card.headOfFamily}\nMobile: ${card.mobile}\nFamily Members: ${card.familyMembers ? card.familyMembers.length : 0}`;
        new QRCode(qrEl, {
          text: qrString,
          width: 55,
          height: 55,
          colorDark: "#1a237e",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    }, 50);
  });

  // Set document.title to head of family name so browser uses it as the default printed filename
  const originalTitle = document.title;
  if (printQueue.length === 1) {
    document.title = `RationCard_${printQueue[0].headOfFamily.replace(/\s+/g, '_')}`;
  } else {
    document.title = `Batch_RationCards_${printQueue.length}_Records`;
  }

  // Trigger browser print dialog
  setTimeout(() => {
    window.print();
    // Restore original page title
    document.title = originalTitle;
  }, 350);
}

/* ==========================================================================
   PDF AUTO-SCANNER & AUTO-IMPORT ENGINE
   ========================================================================== */
async function handlePdfFileSelect() {
  const pdfInput = document.getElementById('pdf-upload');
  if (!pdfInput || !pdfInput.files || !pdfInput.files[0]) return;
  const file = pdfInput.files[0];
  
  const placeholder = document.getElementById('pdf-upload-placeholder');
  const progress = document.getElementById('pdf-upload-progress');
  const success = document.getElementById('pdf-upload-success');
  const error = document.getElementById('pdf-upload-error');
  
  placeholder.classList.add('hidden');
  progress.classList.remove('hidden');
  success.classList.add('hidden');
  error.classList.add('hidden');
  
  try {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result;
        const result = await extractTextAndPhotoFromPdf(arrayBuffer);
        
        fillFormFromParsedData(result);
        
        progress.classList.add('hidden');
        success.classList.remove('hidden');
        
        pdfInput.value = '';
        
        setTimeout(() => {
          success.classList.add('hidden');
          placeholder.classList.remove('hidden');
        }, 4000);
      } catch (err) {
        console.error("Error processing PDF contents:", err);
        showPdfScanError(err.message || "Failed to scan details from this PDF document.");
      }
    };
    reader.onerror = () => {
      showPdfScanError("Failed to read PDF file.");
    };
    reader.readAsArrayBuffer(file);
  } catch (err) {
    console.error("FileReader failed:", err);
    showPdfScanError("FileReader failed.");
  }
}

function showPdfScanError(message) {
  const placeholder = document.getElementById('pdf-upload-placeholder');
  const progress = document.getElementById('pdf-upload-progress');
  const error = document.getElementById('pdf-upload-error');
  const errMessage = document.getElementById('pdf-error-message');
  
  progress.classList.add('hidden');
  error.classList.remove('hidden');
  if (errMessage) errMessage.innerText = message;
  
  setTimeout(() => {
    error.classList.add('hidden');
    placeholder.classList.remove('hidden');
  }, 4000);
}

async function extractTextAndPhotoFromPdf(arrayBuffer) {
  if (typeof pdfjsLib === 'undefined') {
    throw new Error("PDF.js library is not loaded. Please check your internet connection.");
  }
  
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
  
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;
  
  let extractedText = "";
  let photoDataUrl = null;
  
  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();
    
    let pageText = "";
    if (pageNum === 1) {
      pageText = parseTextContentLayout(textContent);
    } else {
      pageText = parseTablePageLayout(textContent);
    }
    
    extractedText += `\n--- Page ${pageNum} Text ---\n` + pageText;
    
    if (pageNum === 1) {
      photoDataUrl = await extractPhotoFromPage(page);
    }
  }
  
  return {
    text: extractedText,
    photo: photoDataUrl
  };
}

function parseTextContentLayout(textContent) {
  const tolerance = 0.5; 
  const lines = [];
  
  const sortedItems = [...textContent.items]
    .filter(item => item.str && item.str.trim() !== '')
    .sort((a, b) => b.transform[5] - a.transform[5]);
    
  sortedItems.forEach(item => {
    const y = item.transform[5];
    let foundLine = lines.find(line => Math.abs(line.y - y) <= tolerance);
    if (!foundLine) {
      foundLine = { y: y, items: [] };
      lines.push(foundLine);
    }
    foundLine.items.push(item);
  });
  
  const textLines = [];
  
  lines.forEach(line => {
    line.items.sort((a, b) => a.transform[4] - b.transform[4]);
    
    let currentLineText = "";
    let lastXEnd = -1;
    
    line.items.forEach(item => {
      const x = item.transform[4];
      const itemWidth = item.width || (item.str.length * 6);
      
      if (lastXEnd !== -1) {
        const gap = x - lastXEnd;
        if (gap > 40.0) {
          textLines.push(currentLineText);
          currentLineText = item.str;
          lastXEnd = x + itemWidth;
          return;
        }
      }
      
      if (currentLineText === "") {
        currentLineText = item.str;
      } else {
        const needsSpace = !currentLineText.endsWith(" ") && !item.str.startsWith(" ");
        currentLineText += (needsSpace ? " " : "") + item.str;
      }
      lastXEnd = x + itemWidth;
    });
    
    if (currentLineText !== "") {
      textLines.push(currentLineText);
    }
  });
  
  return textLines.join("\n");
}

function parseTablePageLayout(textContent) {
  const tolerance = 5.0; 
  const lines = [];
  
  const items = textContent.items.filter(item => item.str && item.str.trim() !== '');
  
  items.forEach(item => {
    const y = item.transform[5];
    let foundLine = lines.find(line => Math.abs(line.y - y) <= tolerance);
    if (!foundLine) {
      foundLine = { y: y, items: [] };
      lines.push(foundLine);
    }
    foundLine.items.push(item);
  });
  
  lines.sort((a, b) => b.y - a.y);
  
  const textLines = [];
  lines.forEach(line => {
    line.items.sort((a, b) => a.transform[4] - b.transform[4]);
    const lineText = line.items.map(item => item.str.trim()).join(" ");
    if (lineText.trim() !== "") {
      textLines.push(lineText);
    }
  });
  
  return textLines.join("\n");
}

async function extractPhotoFromPage(page) {
  try {
    const operatorList = await page.getOperatorList();
    for (let i = 0; i < operatorList.fnArray.length; i++) {
      const fn = operatorList.fnArray[i];
      if (fn === pdfjsLib.OPS.paintImageXObject || fn === pdfjsLib.OPS.paintJpegXObject) {
        const imgKey = operatorList.argsArray[i][0];
        const imgObj = await getImageFromObjs(page, imgKey);
        
        if (imgObj && imgObj.width && imgObj.height && imgObj.data) {
          const dataUrl = convertPdfImageToDataUrl(imgObj);
          if (dataUrl) return dataUrl;
        }
      }
    }
  } catch (err) {
    console.error("Failed to extract photo from operator list:", err);
  }
  return null;
}

function getImageFromObjs(page, imgKey) {
  return new Promise((resolve) => {
    try {
      const img = page.objs.get(imgKey);
      if (img && img.width && img.height && img.data) {
        resolve(img);
        return;
      }
    } catch (e) {}

    try {
      page.objs.get(imgKey, (img) => {
        if (img) {
          resolve(img);
        } else {
          resolve(null);
        }
      });
      return;
    } catch (e) {}

    try {
      const img = page.commonObjs.get(imgKey);
      if (img && img.width && img.height && img.data) {
        resolve(img);
        return;
      }
    } catch (e) {}

    try {
      page.commonObjs.get(imgKey, (img) => {
        resolve(img || null);
      });
      return;
    } catch (e) {}

    resolve(null);
  });
}

function convertPdfImageToDataUrl(pdfImageObj) {
  const canvas = document.createElement('canvas');
  canvas.width = pdfImageObj.width;
  canvas.height = pdfImageObj.height;
  const ctx = canvas.getContext('2d');
  
  const numPixels = pdfImageObj.width * pdfImageObj.height;
  const imgData = ctx.createImageData(pdfImageObj.width, pdfImageObj.height);
  const data = imgData.data;
  const rawData = pdfImageObj.data;
  
  if (rawData.length === numPixels * 3) {
    let srcIdx = 0;
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      data[destIdx] = rawData[srcIdx];       
      data[destIdx + 1] = rawData[srcIdx + 1]; 
      data[destIdx + 2] = rawData[srcIdx + 2]; 
      data[destIdx + 3] = 255;                 
      srcIdx += 3;
      destIdx += 4;
    }
  } else if (rawData.length === numPixels * 4) {
    data.set(rawData);
  } else if (rawData.length === numPixels) {
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      const val = rawData[i];
      data[destIdx] = val;
      data[destIdx + 1] = val;
      data[destIdx + 2] = val;
      data[destIdx + 3] = 255;
      destIdx += 4;
    }
  } else {
    let srcIdx = 0;
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      if (srcIdx < rawData.length) {
        data[destIdx] = rawData[srcIdx];
        data[destIdx + 1] = rawData[srcIdx + 1] !== undefined ? rawData[srcIdx + 1] : rawData[srcIdx];
        data[destIdx + 2] = rawData[srcIdx + 2] !== undefined ? rawData[srcIdx + 2] : rawData[srcIdx];
        data[destIdx + 3] = 255;
      }
      srcIdx += (rawData.length === numPixels * 3) ? 3 : 4;
      destIdx += 4;
    }
  }
  
  ctx.putImageData(imgData, 0, 0);
  
  const maxDim = 300;
  if (canvas.width > maxDim || canvas.height > maxDim) {
    const scaleCanvas = document.createElement('canvas');
    let w = canvas.width;
    let h = canvas.height;
    if (w > h) {
      h = Math.round((h * maxDim) / w);
      w = maxDim;
    } else {
      w = Math.round((w * maxDim) / h);
      h = maxDim;
    }
    scaleCanvas.width = w;
    scaleCanvas.height = h;
    const scaleCtx = scaleCanvas.getContext('2d');
    scaleCtx.drawImage(canvas, 0, 0, w, h);
    return scaleCanvas.toDataURL('image/jpeg', 0.85);
  }
  
  return canvas.toDataURL('image/jpeg', 0.85);
}

function fillFormFromParsedData(result) {
  const text = result.text;
  const photo = result.photo;

  // 1. Ration Card Number (12 digit code, usually on Page 1)
  let cardNumber = "";
  let page1Text = text;
  const page1Index = text.indexOf("--- Page 1 Text ---");
  const page2Index = text.indexOf("--- Page 2 Text ---");
  if (page1Index !== -1) {
    if (page2Index !== -1) {
      page1Text = text.substring(page1Index, page2Index);
    } else {
      page1Text = text.substring(page1Index);
    }
  }
  
  // Try matching pattern starting with 218 first (most common case, 98%+)
  let cardNoMatch = page1Text.match(/(218[\s\d-]{8,16}\d)/);
  if (!cardNoMatch) {
    // Fallback: match any 12-digit pattern (allowing optional spaces or dashes)
    cardNoMatch = page1Text.match(/(\d[\s\d-]{10,18}\d)/);
  }
  
  if (cardNoMatch && cardNoMatch[1]) {
    cardNumber = cardNoMatch[1].replace(/[\s-]+/g, '');
  }

  // 2. Scheme Name
  let schemeName = "";
  const schemeMatch = text.match(/Scheme Name:\s*([^\n]+)/i);
  if (schemeMatch && schemeMatch[1]) {
    schemeName = schemeMatch[1].trim();
  }

  // 3. Head of Family
  let headOfFamily = "";
  const headMatch = text.match(/Head of Family:\s*([^\n]+)/i);
  if (headMatch && headMatch[1]) {
    headOfFamily = headMatch[1].trim();
  }

  // 4. Issue Date (first date pattern on Page 1)
  let issueDate = "";
  const issueMatch = page1Text.match(/(\d{1,2}[\/\s-]\d{1,2}[\/\s-]\d{4})/);
  if (issueMatch && issueMatch[1]) {
    const rawDate = issueMatch[1].trim();
    const parts = rawDate.replace(/[-\s]/g, '/').split('/');
    if (parts.length === 3) {
      const day = parts[0].padStart(2, '0');
      const month = parts[1].padStart(2, '0');
      const year = parts[2];
      issueDate = `${day}/${month}/${year}`;
    } else {
      issueDate = rawDate;
    }
  }

  // 5. Fare Price Shop Number
  let fareShopNumber = "";
  const fpsMatch = text.match(/Fare Price Shop No:\s*([^\n]+)/i);
  if (fpsMatch && fpsMatch[1]) {
    fareShopNumber = fpsMatch[1].trim();
  }

  // 6. Mobile Number
  let mobile = "";
  const mobileMatch = text.match(/Mobile Number:\s*(\d{10})/i);
  if (mobileMatch && mobileMatch[1]) {
    mobile = mobileMatch[1].trim();
  }

  // 7. Address
  let address = "";
  const addressMatch = text.match(/Address:\s*([^\n]+)/i);
  if (addressMatch && addressMatch[1]) {
    address = addressMatch[1].trim();
  }

  // 8. Family Members Rows
  const parsedFamily = parseFamilyMembersFromText(text);

  // Apply to Form inputs
  if (cardNumber) document.getElementById('ration-card-number').value = cardNumber;
  if (schemeName) document.getElementById('scheme-name').value = schemeName;
  if (headOfFamily) document.getElementById('head-of-family').value = headOfFamily;
  if (issueDate) {
    let issueDateFormatted = "";
    const parts = issueDate.split('/');
    if (parts.length === 3) {
      issueDateFormatted = `${parts[2]}-${parts[1]}-${parts[0]}`;
    } else {
      issueDateFormatted = issueDate;
    }
    document.getElementById('issue-date').value = issueDateFormatted;
  }
  if (fareShopNumber) document.getElementById('fare-shop-number').value = fareShopNumber;
  if (mobile) document.getElementById('mobile-number').value = mobile;
  if (address) document.getElementById('address').value = address;

  // Photo apply
  if (photo) {
    const previewImg = document.getElementById('photo-preview-img');
    const uploadPlaceholder = document.querySelector('.upload-placeholder');
    const removeBtn = document.querySelector('.remove-photo-btn');
    
    previewImg.src = photo;
    previewImg.classList.remove('hidden');
    uploadPlaceholder.classList.add('hidden');
    removeBtn.classList.remove('hidden');
    
    document.getElementById('card-photo').src = photo;
  } else {
    removeUploadedPhoto();
  }

  // Populate Family Members Table
  const tableBody = document.querySelector('#family-table tbody');
  tableBody.innerHTML = '';
  
  if (parsedFamily && parsedFamily.length > 0) {
    parsedFamily.forEach(member => {
      addFamilyTableRow(member.sr, member.name, member.age, member.gender, member.relation, member.aadhaar);
    });
  } else {
    addFamilyTableRow();
  }

  updateLivePreview();
}

function parseFamilyMembersFromText(text) {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  const members = [];
  const rowPattern = /^(\d+)\s+(.+?)\s+(\d+)\s*\/\s*([FM])\s+(.+?)\s+([X\d\s-]+)$/i;

  lines.forEach(line => {
    const match = line.match(rowPattern);
    if (match) {
      members.push({
        sr: match[1],
        name: match[2].trim(),
        age: match[3],
        gender: match[4].toUpperCase(),
        relation: match[5].trim(),
        aadhaar: match[6].replace(/\s+/g, '') 
      });
    }
  });

  return members;
}
