// Custom toolbar button order — recording right after chat (middle of tab bar)
config.toolbarButtons = [
    'microphone', 'camera', 'desktop', 'chat', 'recording',
    'raisehand', 'reactions', 'participants-pane', 'tileview',
    'fullscreen', 'settings'
];

// Inject CSS: recording icon turns solid red when active, with pulse
(function() {
    var style = document.createElement('style');
    style.id = 'jitsi-custom-styles';
    style.textContent = [
        /* Recording button — inactive (default) */
        '.toolbox-button[aria-label*="recording"][aria-label*="Start"] .toolbox-icon,',
        '.toolbox-button[aria-label*="recording"][aria-label*="Start"] .toolbox-icon svg {',
        '  color: #aaa !important;',
        '  fill: #aaa !important;',
        '  transition: color 0.25s, fill 0.25s;',
        '}',
        '',
        /* Recording button — active / clicked (recording in progress) */
        '.toolbox-button[aria-label*="recording"][aria-label*="Stop"] .toolbox-icon,',
        '.toolbox-button[aria-label*="recording"][aria-label*="Stop"] .toolbox-icon svg {',
        '  color: #E53935 !important;',
        '  fill: #E53935 !important;',
        '}',
        '',
        /* Pulse animation on the icon while recording */
        '.toolbox-button[aria-label*="recording"][aria-label*="Stop"] .toolbox-icon {',
        '  animation: jitsi-rec-pulse 1.4s ease-in-out infinite;',
        '}',
        '',
        '@keyframes jitsi-rec-pulse {',
        '  0%   { opacity: 1; }',
        '  50%  { opacity: 0.55; }',
        '  100% { opacity: 1; }',
        '}',
    ].join('\n');
    document.head.appendChild(style);
})();
