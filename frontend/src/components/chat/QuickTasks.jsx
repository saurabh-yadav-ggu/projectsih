import React from 'react';

export default function QuickTasks({ onSelectTask }) {
  const tasks = [
    "Build a clone of WhatsApp",
    "Explain about this PDF",
    "Generate an approval note"
  ];

  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '12px', 
      marginTop: '24px',
      flexWrap: 'wrap',
      justifyContent: 'center'
    }}>
      <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: '500', display: 'flex', alignItems: 'center' }}>Quick Task:</span>
      {tasks.map((task, i) => (
        <button 
          key={i} 
          onClick={() => onSelectTask && onSelectTask(task)}
          style={{ 
            padding: '8px 16px',
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '24px',
            fontSize: '13px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            cursor: 'pointer'
          }} 
          className="nav-item"
        >
          {task}
        </button>
      ))}
    </div>
  );
}
