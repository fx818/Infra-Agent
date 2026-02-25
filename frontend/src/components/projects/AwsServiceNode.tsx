import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { getAwsLogo } from '../../utils/awsLogos';

interface AwsNodeData {
    label: string;
    serviceType: string;
    [key: string]: unknown;
}

const AwsServiceNode: React.FC<NodeProps> = memo(({ data, selected }) => {
    const nodeData = data as AwsNodeData;
    const logo = getAwsLogo(nodeData.serviceType || '');
    const accentColor = logo.color;

    return (
        <div
            style={{
                background: `linear-gradient(135deg, ${logo.bg} 0%, #0d1117 100%)`,
                border: `1.5px solid ${selected ? accentColor : accentColor + '40'}`,
                borderRadius: '14px',
                padding: '12px 14px',
                minWidth: '110px',
                maxWidth: '150px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                boxShadow: selected
                    ? `0 0 0 2px ${accentColor}60, 0 8px 32px ${accentColor}20`
                    : `0 4px 16px rgba(0,0,0,0.4), 0 0 0 1px ${accentColor}15`,
                cursor: 'default',
                transition: 'all 0.2s ease',
                position: 'relative',
            }}
        >
            {/* Connection handles */}
            <Handle
                type="target"
                position={Position.Left}
                style={{
                    background: accentColor,
                    border: 'none',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    opacity: 0.7,
                }}
            />
            <Handle
                type="source"
                position={Position.Right}
                style={{
                    background: accentColor,
                    border: 'none',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    opacity: 0.7,
                }}
            />

            {/* Top and bottom handles for vertical layouts */}
            <Handle
                type="target"
                position={Position.Top}
                id="top"
                style={{
                    background: accentColor,
                    border: 'none',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    opacity: 0.7,
                }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom"
                style={{
                    background: accentColor,
                    border: 'none',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    opacity: 0.7,
                }}
            />

            {/* Category label */}
            <span
                style={{
                    position: 'absolute',
                    top: '4px',
                    right: '6px',
                    fontSize: '7px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: accentColor,
                    opacity: 0.7,
                    fontWeight: 700,
                }}
            >
                {logo.category}
            </span>

            {/* AWS SVG Logo */}
            <div
                style={{
                    width: '56px',
                    height: '56px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    filter: `drop-shadow(0 2px 8px ${accentColor}40) brightness(1.4)`,
                }}
                dangerouslySetInnerHTML={{ __html: logo.svg }}
            />

            {/* Service label */}
            <span
                style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color: '#e2e8f0',
                    textAlign: 'center',
                    lineHeight: 1.3,
                    wordBreak: 'break-word',
                    maxWidth: '120px',
                }}
            >
                {nodeData.label}
            </span>
        </div>
    );
});

AwsServiceNode.displayName = 'AwsServiceNode';

export default AwsServiceNode;
