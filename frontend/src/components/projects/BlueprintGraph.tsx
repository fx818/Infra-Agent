import React, { useMemo, useState, useEffect, useCallback } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    Panel,
    BackgroundVariant,
    useNodesState,
    useEdgesState,
    addEdge,
    ReactFlowProvider,
    useReactFlow,
    MarkerType,
} from '@xyflow/react';
import type { Edge, Node, Connection } from '@xyflow/react';
import dagre from 'dagre';
import { Maximize2, Minimize2, Share2 } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import type { VisualGraph } from '../../types';
import AwsServiceNode from './AwsServiceNode';
import { categoryColors } from '../../utils/awsLogos';

interface Props {
    visualData: VisualGraph;
}

// ── Custom node types ──────────────────────────────────────────────
const nodeTypes = {
    awsService: AwsServiceNode,
};

// ── Dagre auto-layout ──────────────────────────────────────────────
const NODE_WIDTH = 120;
const NODE_HEIGHT = 100;

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({
        rankdir: 'LR',     // left-to-right flow
        ranksep: 80,        // horizontal gap between ranks
        nodesep: 40,        // vertical gap between nodes
        marginx: 40,
        marginy: 40,
    });

    nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
    edges.forEach((e) => g.setEdge(e.source, e.target));

    dagre.layout(g);

    return nodes.map((n) => {
        const { x, y } = g.node(n.id);
        return {
            ...n,
            position: {
                x: x - NODE_WIDTH / 2,
                y: y - NODE_HEIGHT / 2,
            },
        };
    });
}

// ── Category legend ────────────────────────────────────────────────
const LEGEND_CATEGORIES = [
    { label: 'Compute', color: '#FF9900' },
    { label: 'Storage', color: '#3F8624' },
    { label: 'Database', color: '#527FFF' },
    { label: 'Networking', color: '#8C4FFF' },
    { label: 'Messaging', color: '#E7157B' },
    { label: 'Security', color: '#DD344C' },
    { label: 'Monitoring', color: '#E7157B' },
];

import { createPortal } from 'react-dom';

// ── GraphInner ─────────────────────────────────────────────────────
const GraphInner: React.FC<{
    nodes: Node[];
    edges: Edge[];
    onNodesChange: any;
    onEdgesChange: any;
    onConnect: any;
    isFullScreen: boolean;
    toggleFullScreen: () => void;
}> = ({ nodes, edges, onNodesChange, onEdgesChange, onConnect, isFullScreen, toggleFullScreen }) => {
    const { fitView } = useReactFlow();

    // Re-fire fitView when nodes or fullscreen state changes
    useEffect(() => {
        if (nodes.length > 0) {
            // Short delay to ensure the container has settled after portal move
            const timer = setTimeout(() => {
                fitView({ duration: 400, padding: 0.15 });
            }, 50);
            return () => clearTimeout(timer);
        }
    }, [nodes.length, fitView, isFullScreen]);

    // Escape key exits fullscreen
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isFullScreen) toggleFullScreen();
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [isFullScreen, toggleFullScreen]);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            colorMode="dark"
            nodesDraggable
            elementsSelectable
            minZoom={0.1}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
        >
            <Background
                variant={BackgroundVariant.Dots}
                gap={24}
                size={1.2}
                color="#ffffff08"
            />
            <Controls
                showInteractive={false}
                style={{
                    background: 'rgba(13,17,23,0.8)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px',
                }}
            />
            <MiniMap
                style={{
                    background: '#0d1117',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px',
                }}
                nodeColor={(n) => {
                    const serviceType = (n.data as { serviceType?: string }).serviceType || '';
                    const cat = Object.entries(categoryColors).find(([, _]) => {
                        return serviceType.includes(_.toLowerCase().slice(0, 4));
                    });
                    return cat ? cat[1] : '#334155';
                }}
                maskColor="rgba(0,0,0,0.35)"
            />
            <Panel position="top-right" className="flex flex-col gap-2">
                <div style={{
                    background: 'rgba(13,17,23,0.85)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '10px',
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                }}>
                    <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', fontWeight: 700 }}>
                        AWS Architecture
                    </p>
                    <button
                        onClick={toggleFullScreen}
                        style={{
                            padding: '4px 6px',
                            borderRadius: '6px',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'rgba(255,255,255,0.5)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                        }}
                        title={isFullScreen ? 'Exit Full Screen' : 'Full Screen'}
                    >
                        {isFullScreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                    </button>
                </div>

                <div style={{
                    background: 'rgba(13,17,23,0.85)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '10px',
                    padding: '8px 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                }}>
                    <p style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.25)', fontWeight: 700, marginBottom: '4px' }}>
                        Categories
                    </p>
                    {LEGEND_CATEGORIES.map((cat) => (
                        <div key={cat.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: cat.color, flexShrink: 0 }} />
                            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>{cat.label}</span>
                        </div>
                    ))}
                </div>
            </Panel>
        </ReactFlow>
    );
};

// ── Main export ────────────────────────────────────────────────────
export const BlueprintGraph: React.FC<Props> = ({ visualData }) => {
    const [isFullScreen, setIsFullScreen] = useState(false);

    const rawNodes: Node[] = useMemo(() => {
        if (!visualData?.nodes) return [];
        return visualData.nodes.map((node) => ({
            id: node.id,
            type: 'awsService',
            position: node.position || { x: 0, y: 0 },
            data: {
                label: node.data?.label || node.id,
                serviceType: node.data?.service_type || '',
            },
        }));
    }, [visualData?.nodes]);

    const rawEdges: Edge[] = useMemo(() => {
        if (!visualData?.edges) return [];
        return visualData.edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            animated: edge.animated ?? true,
            type: 'smoothstep',
            style: {
                stroke: 'rgba(255,255,255,0.18)',
                strokeWidth: 1.5,
                ...(edge.style || {}),
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: 'rgba(255,255,255,0.3)',
                width: 16,
                height: 16,
            },
            labelStyle: {
                fill: 'rgba(255,255,255,0.4)',
                fontSize: '9px',
                fontWeight: 600,
            },
            labelBgStyle: {
                fill: 'rgba(13,17,23,0.8)',
                stroke: 'rgba(255,255,255,0.06)',
                strokeWidth: 1,
                rx: 4,
                ry: 4,
            },
        }));
    }, [visualData?.edges]);

    const layoutedNodes = useMemo(() => {
        if (rawNodes.length === 0) return [];
        return applyDagreLayout(rawNodes, rawEdges);
    }, [rawNodes, rawEdges]);

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(rawEdges);

    useEffect(() => {
        setNodes(layoutedNodes);
        setEdges(rawEdges);
    }, [layoutedNodes, rawEdges, setNodes, setEdges]);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    const toggleFullScreen = () => setIsFullScreen(!isFullScreen);

    const graphContent = (
        <ReactFlowProvider>
            <GraphInner
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                isFullScreen={isFullScreen}
                toggleFullScreen={toggleFullScreen}
            />
        </ReactFlowProvider>
    );

    const fullScreenContent = isFullScreen ? createPortal(
        <div style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            background: '#0d1117',
            display: 'flex',
            flexDirection: 'column',
        }}>
            <div style={{
                padding: '12px 20px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(13,17,23,0.6)',
                backdropFilter: 'blur(20px)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(99,102,241,0.15)', display: 'flex' }}>
                        <Share2 size={16} color="#6366f1" />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>Full Screen Blueprint</h2>
                        <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', margin: 0 }}>AWS Infrastructure Architecture</p>
                    </div>
                </div>
                <button
                    onClick={toggleFullScreen}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 14px',
                        borderRadius: '8px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.7)',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    <Minimize2 size={13} />
                    <span>Exit Full Screen</span>
                </button>
            </div>
            <div style={{ flex: 1, position: 'relative' }}>{graphContent}</div>
        </div>,
        document.body
    ) : null;

    return (
        <div style={{ width: '100%', height: '100%', background: '#0d1117', position: 'relative' }}>
            {graphContent}
            {fullScreenContent}
        </div>
    );
};
