(() => {
  const form = document.querySelector('[data-sign-form]');
  if (!form) return;
  const canvas = document.getElementById('signature-pad');
  const hidden = document.getElementById('signature-data');
  const clear = document.querySelector('.clear-sign');
  if (!canvas || !hidden) return;
  const ctx = canvas.getContext('2d');
  const bg = () => {ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, canvas.width, canvas.height);};
  bg();
  ctx.strokeStyle = '#76584e'; ctx.lineWidth = 3; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  let drawing = false, touched = false;
  const point = (evt) => {
    const rect = canvas.getBoundingClientRect();
    return {x: (evt.clientX - rect.left) * canvas.width / rect.width,
            y: (evt.clientY - rect.top) * canvas.height / rect.height};
  };
  canvas.addEventListener('pointerdown', evt => {
    evt.preventDefault(); canvas.setPointerCapture(evt.pointerId); drawing = true;
    const p = point(evt); ctx.beginPath(); ctx.moveTo(p.x, p.y);
  });
  canvas.addEventListener('pointermove', evt => {
    if (!drawing) return;
    evt.preventDefault(); const p = point(evt); ctx.lineTo(p.x, p.y); ctx.stroke(); touched = true;
  });
  const done = () => drawing = false;
  canvas.addEventListener('pointerup', done);
  canvas.addEventListener('pointercancel', done);
  clear?.addEventListener('click', () => {ctx.clearRect(0, 0, canvas.width, canvas.height); bg(); ctx.strokeStyle='#76584e'; touched=false; hidden.value='';});
  form.addEventListener('submit', evt => {
    if (!touched) {evt.preventDefault(); alert('인수자의 확인 서명을 입력해 주세요.');return;}
    hidden.value = canvas.toDataURL('image/png');
  });
})();
