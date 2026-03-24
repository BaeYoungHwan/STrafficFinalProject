<template>
  <router-view />
</template>

<script setup>
</script>

<style>
/* ===== Custom Cursor (Blueness Insanity) ===== */
* {
  box-sizing: border-box;
  cursor: url('/cursors/Blueness.cur'), default;
}

a,
button,
[role="button"],
label[for],
.clickable {
  cursor: url('/cursors/Blueness_Link.cur'), pointer;
}

input[type="text"],
input[type="email"],
input[type="password"],
input[type="number"],
input[type="search"],
textarea,
[contenteditable] {
  cursor: url('/cursors/Blueness_text.cur'), text;
}

[title],
abbr,
.help {
  cursor: url('/cursors/Blueness_Help.cur'), help;
}

[draggable],
.draggable,
.drag-handle {
  cursor: url('/cursors/Blueness_Move.cur'), move;
}

:disabled,
[disabled],
.disabled {
  cursor: url('/cursors/Blueness_unav.cur'), not-allowed;
}

.alias {
  cursor: url('/cursors/Blueness_Alt.cur'), alias;
}

.resize-nwse {
  cursor: url('/cursors/Blueness_Diag1.cur'), nwse-resize;
}

.resize-nesw {
  cursor: url('/cursors/Blueness_Diag2.cur'), nesw-resize;
}

.resize-ew {
  cursor: url('/cursors/Blueness_LeftRight.cur'), ew-resize;
}

.resize-ns {
  cursor: url('/cursors/Blueness_UpDown.cur'), ns-resize;
}

.loading,
[aria-busy="true"] {
  cursor: url('/cursors/Blueness_Load.ani'), wait;
}

html,
body,
#app {
  width: 100%;
  min-height: 100%;
  margin: 0;
  padding: 0;
}

body {
  min-width: 320px;
  background: #FFFFFF;
  font-family: 'Pretendard', 'Noto Sans KR', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1A1A2E;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: inherit;
  text-decoration: none;
}

button,
input,
textarea,
select {
  font: inherit;
}
</style>
