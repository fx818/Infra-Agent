import React, { useState, useCallback, useRef, useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    BackgroundVariant,
    useNodesState,
    useEdgesState,
    addEdge,
    ReactFlowProvider,
    MarkerType,
    Panel,
} from '@xyflow/react';
import type { Edge, Node, Connection, ReactFlowInstance } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
    Search, Save, Blocks, ChevronDown, ChevronRight,
    GripVertical, Loader2, Undo2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getAwsLogo } from '../utils/awsLogos';
import {
    CATEGORY_COLORS,
    getServicesByCategory,
} from '../utils/awsServiceCatalog';
import type { AwsServiceDef } from '../utils/awsServiceCatalog';
import { isConnectionAllowed, getConnectionLabel } from '../utils/awsConnections';
import DragBuildNode from '../components/drag-build/DragBuildNode';
import api from '../api/client';

// ── Node types ─────────────────────────────────────────────────────
const nodeTypes = { dragBuildNode: DragBuildNode };

let nodeIdCounter = 0;
function nextNodeId() {
    return `node_${++nodeIdCounter}_${Date.now()}`;
}

// ── Main Component ─────────────────────────────────────────────────
const DragBuildInner: React.FC = () => {
    const navigate = useNavigate();
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);

    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

    const [projectName, setProjectName] = useState('');
    const [projectDesc, setProjectDesc] = useState('');
    const [saving, setSaving] = useState(false);
    const [search, setSearch] = useState('');
    const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set());

    // ── Service catalog filtering ──────────────────────────────────
    const servicesByCategory = useMemo(() => getServicesByCategory(), []);
    const filteredServices = useMemo(() => {
        if (!search.trim()) return servicesByCategory;
        const q = search.toLowerCase();
        const filtered: Record<string, AwsServiceDef[]> = {};
        for (const [cat, svcs] of Object.entries(servicesByCategory)) {
            const matched = svcs.filter(
                s => s.name.toLowerCase().includes(q) ||
                    s.description.toLowerCase().includes(q) ||
                    s.id.toLowerCase().includes(q)
            );
            if (matched.length) filtered[cat] = matched;
        }
        return filtered;
    }, [search, servicesByCategory]);

    // ── Drag and drop ──────────────────────────────────────────────
    const onDragStart = (e: React.DragEvent, service: AwsServiceDef) => {
        e.dataTransfer.setData('application/json', JSON.stringify(service));
        e.dataTransfer.effectAllowed = 'move';
    };

    const onDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            const data = e.dataTransfer.getData('application/json');
            if (!data || !rfInstance) return;

            const service: AwsServiceDef = JSON.parse(data);
            const bounds = reactFlowWrapper.current?.getBoundingClientRect();
            if (!bounds) return;

            const position = rfInstance.screenToFlowPosition({
                x: e.clientX - bounds.left,
                y: e.clientY - bounds.top,
            });

            const newNode: Node = {
                id: nextNodeId(),
                type: 'dragBuildNode',
                position,
                data: {
                    label: service.name,
                    serviceType: service.id,
                    serviceDef: service,
                    onDelete: (id: string) => setNodes(ns => ns.filter(n => n.id !== id)),
                },
            };

            setNodes(ns => [...ns, newNode]);
        },
        [rfInstance, setNodes]
    );

    // ── Connection validation ──────────────────────────────────────
    const onConnect = useCallback(
        (params: Connection) => {
            const sourceNode = nodes.find(n => n.id === params.source);
            const targetNode = nodes.find(n => n.id === params.target);
            if (!sourceNode || !targetNode) return;

            const srcType = (sourceNode.data as any).serviceType;
            const tgtType = (targetNode.data as any).serviceType;

            if (!isConnectionAllowed(srcType, tgtType)) {
                // TODO: could show toast — for now silently reject
                return;
            }

            const label = getConnectionLabel(srcType, tgtType);
            const edge: Edge = {
                id: `e_${params.source}_${params.target}`,
                source: params.source!,
                target: params.target!,
                label,
                animated: true,
                type: 'smoothstep',
                style: { stroke: 'rgba(255,255,255,0.25)', strokeWidth: 1.5 },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: 'rgba(255,255,255,0.4)',
                    width: 16,
                    height: 16,
                },
                labelStyle: { fill: 'rgba(255,255,255,0.5)', fontSize: '9px', fontWeight: 600 },
                labelBgStyle: {
                    fill: 'rgba(13,17,23,0.85)',
                    stroke: 'rgba(255,255,255,0.06)',
                    strokeWidth: 1,
                    rx: 4,
                    ry: 4,
                },
            };

            setEdges(eds => addEdge(edge, eds));
        },
        [nodes, setEdges]
    );

    // ── Keyboard shortcuts ─────────────────────────────────────────
    const onKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                setNodes(ns => ns.filter(n => !n.selected));
                setEdges(es => es.filter(e2 => !e2.selected));
            }
        },
        [setNodes, setEdges]
    );

    // ── Save ───────────────────────────────────────────────────────
    const handleSave = async () => {
        if (!projectName.trim() || nodes.length === 0) return;
        setSaving(true);
        try {
            const payload = {
                name: projectName.trim(),
                description: projectDesc.trim() || undefined,
                region: 'us-east-1',
                nodes: nodes.map(n => ({
                    id: n.id,
                    type: (n.data as any).serviceType,
                    label: (n.data as any).label,
                    position: n.position,
                    config: (n.data as any).serviceDef?.defaultConfig || {},
                })),
                edges: edges.map(e => ({
                    id: e.id,
                    source: e.source,
                    target: e.target,
                    label: (e.label as string) || '',
                })),
            };
            const res = await api.post('/drag-build/save', payload);
            navigate(`/projects/${res.data.id}`);
        } catch (err) {
            console.error('Failed to save drag build:', err);
        } finally {
            setSaving(false);
        }
    };

    // ── Clear canvas ───────────────────────────────────────────────
    const handleClear = () => {
        if (nodes.length === 0) return;
        if (!window.confirm('Clear the entire canvas?')) return;
        setNodes([]);
        setEdges([]);
    };

    const toggleCategory = (cat: string) => {
        setCollapsedCats(prev => {
            const next = new Set(prev);
            next.has(cat) ? next.delete(cat) : next.add(cat);
            return next;
        });
    };

    return (
        <div style={{ display: 'flex', height: '100%', gap: 0 }}>
            {/* ═══ Left Toolbar ═══ */}
            <div style={{
                width: '280px',
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                background: 'rgba(13,17,23,0.6)',
                borderRight: '1px solid rgba(255,255,255,0.06)',
                overflow: 'hidden',
            }}>
                {/* Header */}
                <div style={{
                    padding: '16px',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                        <div style={{
                            width: '32px', height: '32px', borderRadius: '10px',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <Blocks size={16} color="white" />
                        </div>
                        <div>
                            <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
                                AWS Services
                            </h3>
                            <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', margin: 0 }}>
                                Drag to canvas
                            </p>
                        </div>
                    </div>

                    {/* Search */}
                    <div style={{ position: 'relative' }}>
                        <Search size={13} style={{
                            position: 'absolute', left: '10px', top: '50%',
                            transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.25)',
                        }} />
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Search services…"
                            style={{
                                width: '100%', padding: '8px 10px 8px 32px',
                                background: 'rgba(255,255,255,0.04)',
                                border: '1px solid rgba(255,255,255,0.08)',
                                borderRadius: '8px', color: '#e2e8f0', fontSize: '12px',
                                outline: 'none', colorScheme: 'dark',
                            }}
                        />
                    </div>
                </div>

                {/* Service list */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
                    {Object.entries(filteredServices).map(([cat, services]) => (
                        <div key={cat} style={{ marginBottom: '4px' }}>
                            {/* Category header */}
                            <button
                                onClick={() => toggleCategory(cat)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: '6px',
                                    width: '100%', padding: '6px 8px',
                                    background: 'none', border: 'none',
                                    color: CATEGORY_COLORS[cat] || 'rgba(255,255,255,0.5)',
                                    fontSize: '10px', fontWeight: 700,
                                    textTransform: 'uppercase', letterSpacing: '0.06em',
                                    cursor: 'pointer',
                                }}
                            >
                                {collapsedCats.has(cat) ?
                                    <ChevronRight size={12} /> :
                                    <ChevronDown size={12} />
                                }
                                <span style={{
                                    width: '6px', height: '6px', borderRadius: '50%',
                                    background: CATEGORY_COLORS[cat] || '#64748b',
                                }} />
                                {cat}
                                <span style={{
                                    fontSize: '9px', color: 'rgba(255,255,255,0.15)',
                                    marginLeft: 'auto', fontWeight: 500,
                                }}>
                                    {services.length}
                                </span>
                            </button>

                            {/* Service cards */}
                            {!collapsedCats.has(cat) && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', paddingLeft: '8px' }}>
                                    {services.map(svc => {
                                        const logo = getAwsLogo(svc.id);
                                        return (
                                            <div
                                                key={svc.id}
                                                draggable
                                                onDragStart={e => onDragStart(e, svc)}
                                                style={{
                                                    display: 'flex', alignItems: 'center', gap: '10px',
                                                    padding: '8px 10px',
                                                    background: 'rgba(255,255,255,0.02)',
                                                    border: '1px solid rgba(255,255,255,0.04)',
                                                    borderRadius: '8px',
                                                    cursor: 'grab',
                                                    transition: 'all 0.15s ease',
                                                }}
                                                onMouseEnter={e => {
                                                    (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.06)';
                                                    (e.currentTarget as HTMLDivElement).style.borderColor = `${logo.color}40`;
                                                }}
                                                onMouseLeave={e => {
                                                    (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.02)';
                                                    (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.04)';
                                                }}
                                            >
                                                <GripVertical size={12} color="rgba(255,255,255,0.15)" />
                                                <div
                                                    style={{
                                                        width: '28px', height: '28px',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                        filter: `brightness(1.3)`,
                                                        flexShrink: 0,
                                                    }}
                                                    dangerouslySetInnerHTML={{ __html: logo.svg }}
                                                />
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <p style={{
                                                        fontSize: '11px', fontWeight: 600, color: '#e2e8f0',
                                                        margin: 0, lineHeight: 1.2,
                                                    }}>
                                                        {svc.name}
                                                    </p>
                                                    <p style={{
                                                        fontSize: '9px', color: 'rgba(255,255,255,0.3)',
                                                        margin: 0, lineHeight: 1.3,
                                                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                                                    }}>
                                                        {svc.description}
                                                    </p>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* ═══ Canvas Area ═══ */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                {/* Top toolbar */}
                <div style={{
                    padding: '10px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex', alignItems: 'center', gap: '12px',
                    background: 'rgba(13,17,23,0.5)',
                    backdropFilter: 'blur(12px)',
                }}>
                    <input
                        type="text"
                        value={projectName}
                        onChange={e => setProjectName(e.target.value)}
                        placeholder="Project name…"
                        style={{
                            background: 'rgba(255,255,255,0.04)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: '8px', padding: '8px 14px',
                            color: '#f1f5f9', fontSize: '13px', fontWeight: 600,
                            width: '260px', outline: 'none', colorScheme: 'dark',
                        }}
                    />
                    <input
                        type="text"
                        value={projectDesc}
                        onChange={e => setProjectDesc(e.target.value)}
                        placeholder="Description (optional)…"
                        style={{
                            background: 'rgba(255,255,255,0.04)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: '8px', padding: '8px 14px',
                            color: '#e2e8f0', fontSize: '12px',
                            flex: 1, outline: 'none', colorScheme: 'dark',
                        }}
                    />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: 'auto' }}>
                        {/* Node count badge */}
                        <span style={{
                            padding: '4px 10px', borderRadius: '20px',
                            background: 'rgba(99,102,241,0.12)',
                            border: '1px solid rgba(99,102,241,0.2)',
                            color: '#818cf8', fontSize: '11px', fontWeight: 700,
                        }}>
                            {nodes.length} nodes • {edges.length} edges
                        </span>

                        <button
                            onClick={handleClear}
                            disabled={nodes.length === 0}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '5px',
                                padding: '6px 12px', borderRadius: '8px',
                                background: 'rgba(239,68,68,0.08)',
                                border: '1px solid rgba(239,68,68,0.2)',
                                color: '#f87171', fontSize: '11px', fontWeight: 600,
                                cursor: nodes.length === 0 ? 'not-allowed' : 'pointer',
                                opacity: nodes.length === 0 ? 0.4 : 1,
                            }}
                        >
                            <Undo2 size={12} /> Clear
                        </button>

                        <button
                            onClick={handleSave}
                            disabled={saving || !projectName.trim() || nodes.length === 0}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '6px',
                                padding: '6px 16px', borderRadius: '8px',
                                background: saving ? 'rgba(99,102,241,0.1)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                border: 'none',
                                color: 'white', fontSize: '12px', fontWeight: 700,
                                cursor: saving || !projectName.trim() || nodes.length === 0 ? 'not-allowed' : 'pointer',
                                opacity: !projectName.trim() || nodes.length === 0 ? 0.4 : 1,
                                boxShadow: '0 2px 12px rgba(99,102,241,0.3)',
                            }}
                        >
                            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                            {saving ? 'Saving…' : 'Save Project'}
                        </button>
                    </div>
                </div>

                {/* ReactFlow canvas */}
                <div
                    ref={reactFlowWrapper}
                    style={{ flex: 1, background: '#0a0e14' }}
                    onDragOver={onDragOver}
                    onDrop={onDrop}
                    onKeyDown={onKeyDown}
                    tabIndex={0}
                >
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        onInit={setRfInstance}
                        nodeTypes={nodeTypes}
                        fitView
                        colorMode="dark"
                        nodesDraggable
                        elementsSelectable
                        deleteKeyCode={['Delete', 'Backspace']}
                        minZoom={0.1}
                        maxZoom={3}
                        proOptions={{ hideAttribution: true }}
                    >
                        <Background
                            variant={BackgroundVariant.Dots}
                            gap={20}
                            size={1}
                            color="#ffffff06"
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
                            nodeColor={n => {
                                const svcType = (n.data as any)?.serviceType || '';
                                const logo = getAwsLogo(svcType);
                                return logo.color;
                            }}
                            maskColor="rgba(0,0,0,0.35)"
                        />

                        {/* Empty state */}
                        {nodes.length === 0 && (
                            <Panel position="top-center">
                                <div style={{
                                    textAlign: 'center', padding: '60px 40px',
                                    color: 'rgba(255,255,255,0.15)',
                                }}>
                                    <Blocks size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
                                    <p style={{ fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>
                                        Drag AWS services here
                                    </p>
                                    <p style={{ fontSize: '11px', opacity: 0.6 }}>
                                        Build your infrastructure by dragging services from the left panel
                                    </p>
                                </div>
                            </Panel>
                        )}
                    </ReactFlow>
                </div>
            </div>
        </div>
    );
};

// ── Exported page ──────────────────────────────────────────────────
export const DragBuild: React.FC = () => (
    <ReactFlowProvider>
        <DragBuildInner />
    </ReactFlowProvider>
);

export default DragBuild;
