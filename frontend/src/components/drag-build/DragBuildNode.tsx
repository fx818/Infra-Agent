import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { X } from 'lucide-react';
import { getAwsLogo } from '../../utils/awsLogos';

interface DragBuildNodeData {
    label: string;
    serviceType: string;
    serviceDef?: any;
    onDelete?: (id: string) => void;
    [key: string]: unknown;
}

const DragBuildNode: React.FC<NodeProps> = memo(({ id, data, selected }) => {
    const nodeData = data as DragBuildNodeData;
    const logo = getAwsLogo(nodeData.serviceType || '');
    const accentColor = logo.color;

    return (
        <div
            style={{
                background: `linear-gradient(145deg, ${logo.bg} 0%, #0d1117 100%)`,
                border: `2px solid ${selected ? accentColor : accentColor + '35'}`,
                borderRadius: '16px',
                padding: '14px 16px',
                minWidth: '140px',
                maxWidth: '180px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                boxShadow: selected
                    ? `0 0 0 3px ${accentColor}40, 0 12px 40px ${accentColor}25`
                    : `0 6px 24px rgba(0,0,0,0.5), 0 0 0 1px ${accentColor}10`,
                cursor: 'grab',
                transition: 'all 0.2s ease',
                position: 'relative',
            }}
        >
            {/* Handles */}
            <Handle
                type="target"
                position={Position.Left}
                style={{
                    background: accentColor, border: '2px solid #0d1117',
                    width: '10px', height: '10px', borderRadius: '50%',
                }}
            />
            <Handle
                type="source"
                position={Position.Right}
                style={{
                    background: accentColor, border: '2px solid #0d1117',
                    width: '10px', height: '10px', borderRadius: '50%',
                }}
            />
            <Handle
                type="target"
                position={Position.Top}
                id="top"
                style={{
                    background: accentColor, border: '2px solid #0d1117',
                    width: '10px', height: '10px', borderRadius: '50%',
                }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom"
                style={{
                    background: accentColor, border: '2px solid #0d1117',
                    width: '10px', height: '10px', borderRadius: '50%',
                }}
            />

            {/* Delete button — appears on hover via CSS */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    nodeData.onDelete?.(id);
                }}
                className="drag-build-delete-btn"
                style={{
                    position: 'absolute', top: '-8px', right: '-8px',
                    width: '20px', height: '20px', borderRadius: '50%',
                    background: '#ef4444', border: '2px solid #0d1117',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', opacity: selected ? 1 : 0,
                    transition: 'opacity 0.15s',
                    zIndex: 10,
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
            >
                <X size={10} color="white" />
            </button>

            {/* Category badge */}
            <span
                style={{
                    position: 'absolute', top: '6px', right: '10px',
                    fontSize: '7px', textTransform: 'uppercase',
                    letterSpacing: '0.05em', color: accentColor,
                    opacity: 0.8, fontWeight: 700,
                }}
            >
                {logo.category}
            </span>

            {/* Logo */}
            <div
                style={{
                    width: '52px', height: '52px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    filter: `drop-shadow(0 2px 8px ${accentColor}40) brightness(1.4)`,
                    marginTop: '4px',
                }}
                dangerouslySetInnerHTML={{ __html: logo.svg }}
            />

            {/* Label */}
            <span
                style={{
                    fontSize: '11px', fontWeight: 700, color: '#f1f5f9',
                    textAlign: 'center', lineHeight: 1.3,
                    wordBreak: 'break-word', maxWidth: '140px',
                }}
            >
                {nodeData.label}
            </span>

            {/* Service ID subtitle */}
            <span
                style={{
                    fontSize: '8px', color: 'rgba(255,255,255,0.2)',
                    fontFamily: 'monospace',
                }}
            >
                {nodeData.serviceType}
            </span>
        </div>
    );
});

DragBuildNode.displayName = 'DragBuildNode';

export default DragBuildNode;
