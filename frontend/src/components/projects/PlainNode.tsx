import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

/** Fallback plain text node for any nodes that don't match an AWS type */
const PlainNode: React.FC<NodeProps> = memo(({ data, selected }) => {
    const label = (data as { label?: string }).label || '';
    return (
        <div
            style={{
                background: '#161b22',
                border: `1.5px solid ${selected ? '#6366f1' : '#30363d'}`,
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '11px',
                fontWeight: 600,
                color: '#e2e8f0',
                minWidth: '80px',
                textAlign: 'center',
                boxShadow: selected ? '0 0 0 2px #6366f140' : '0 2px 8px rgba(0,0,0,0.3)',
            }}
        >
            <Handle type="target" position={Position.Left} style={{ background: '#6366f1' }} />
            <Handle type="source" position={Position.Right} style={{ background: '#6366f1' }} />
            {label}
        </div>
    );
});

PlainNode.displayName = 'PlainNode';
export default PlainNode;
