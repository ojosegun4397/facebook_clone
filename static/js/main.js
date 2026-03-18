/**
 * ================================================
 * FACEBOOK CLONE - main.js
 * Handles all interactive features:
 *   - Liking posts (no page reload)
 *   - Adding comments (no page reload)
 *   - Opening/closing modals
 *   - Dropdown menus
 * ================================================
 */

// ------------------------------------------------
// LIKE TOGGLE
// ------------------------------------------------
async function toggleLike(postId, btn) {
  try {
    const response = await fetch(/like/${postId}, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();

    // Update the like count
    const countEl = document.getElementById(like-count-${postId});
    if (countEl) countEl.textContent = data.count;

    // Change button appearance
    const icon = btn.querySelector('i');
    if (data.liked) {
      btn.classList.add('liked');
      if (icon) { 
        icon.classList.remove('far'); 
        icon.classList.add('fas'); 
      }
    } else {
      btn.classList.remove('liked');
      if (icon) { 
        icon.classList.remove('fas'); 
        icon.classList.add('far'); 
      }
    }

    // Little bounce animation
    btn.style.transform = 'scale(1.2)';
    setTimeout(() => btn.style.transform = '', 150);

  } catch (err) {
    console.error('Like failed:', err);
  }
}


// ------------------------------------------------
// TOGGLE COMMENTS SECTION
// ------------------------------------------------
function toggleComments(postId) {
  const section = document.getElementById(comments-${postId});
  if (!section) return;

  if (section.style.display === 'none' || !section.style.display) {
    section.style.display = 'block';
    const input = document.getElementById(comment-input-${postId});
    if (input) input.focus();
  } else {
    section.style.display = 'none';
  }
}


// ------------------------------------------------
// SUBMIT COMMENT - Press Enter to post
// ------------------------------------------------
async function submitComment(event, postId) {
  if (event.key !== 'Enter' && event.keyCode !== 13) return;

  const input = document.getElementById(comment-input-${postId});
  const content = input.value.trim();
  if (!content) return;

  try {
    const response = await fetch(/comment/${postId}, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });

    const data = await response.json();
    if (data.error) return;

    // Add comment to page without reloading
    const section = document.getElementById(comments-${postId});
    const addCommentDiv = section.querySelector('.add-comment');

    const commentHTML = `
      <div class="comment">
        <img src="/static/images/default.png" class="comment-avatar"/>
        <div class="comment-bubble">
          <span class="comment-name">
            ${data.first_name} ${data.last_name}
          </span>
          <p>${escapeHtml(data.content)}</p>
        </div>
      </div>
    `;
    addCommentDiv.insertAdjacentHTML('beforebegin', commentHTML);

    // Update comment count
    const postEl = document.getElementById(post-${postId});
    if (postEl) {
      const countEl = postEl.querySelector('.comment-stat');
      if (countEl) {
        const current = parseInt(countEl.textContent) || 0;
        countEl.textContent = ${current + 1} Comment${current + 1 !== 1 ? 's' : ''};
      }
    }

    // Clear the input box
    input.value = '';

  } catch (err) {
    console.error('Comment failed:', err);
  }
}


// ------------------------------------------------
// ESCAPE HTML - Prevent XSS attacks
// ------------------------------------------------
function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}


// ------------------------------------------------
// MODAL OPEN/CLOSE
// ------------------------------------------------
function closeModal(event) {
  if (event.target === event.currentTarget) {
    event.currentTarget.style.display = 'none';
  }
}

// Close modals with Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay').forEach(m => {
      m.style.display = 'none';
    });
  }
});


// ------------------------------------------------
// FEELING MODAL
// ------------------------------------------------
function openFeelingModal() {
  document.getElementById('post-modal').style.display = 'none';
  document.getElementById('feeling-modal').style.display = 'flex';
}

function closeFeelingModal(event) {
  if (event.target === event.currentTarget) {
    document.getElementById('feeling-modal').style.display = 'none';
  }
}

function selectFeeling(feeling) {
  const input = document.getElementById('selected-feeling');
  if (input) input.value = feeling;

  const chips = document.getElementById('feeling-chips');
  if (chips) {
    chips.innerHTML = <span class="feeling-chip-tag">${feeling}</span>;
  }

  document.getElementById('feeling-modal').style.display = 'none';
  document.getElementById('post-modal').style.display = 'flex';
}


// ------------------------------------------------
// POST DROPDOWN MENUS (3 dot menu)
// ------------------------------------------------
function toggleMenu(postId) {
  const menu = document.getElementById(menu-${postId});
  if (!menu) return;

  // Close all other menus first
  document.querySelectorAll('.post-dropdown').forEach(m => {
    if (m !== menu) m.classList.remove('open');
  });

  menu.classList.toggle('open');
}

// Click anywhere else to close dropdowns
document.addEventListener('click', function(e) {
  if (!e.target.closest('.post-menu')) {
    document.querySelectorAll('.post-dropdown').forEach(m => {
      m.classList.remove('open');
    });
  }
});


// ------------------------------------------------
// AUTO DISMISS FLASH MESSAGES after 4 seconds
// ------------------------------------------------
setTimeout(function() {
  document.querySelectorAll('.flash').forEach(f => {
    f.style.opacity = '0';
    f.style.transition = 'opacity 0.3s';
    setTimeout(() => f.remove(), 300);
  });
}, 4000);


console.log('🚀 Facebook Clone JS loaded!');