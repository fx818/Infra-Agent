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
} from '@xyflow/react';
import type { Edge, Node, Connection } from '@xyflow/react';
import { Maximize2, Minimize2, Share2 } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import type { VisualGraph } from '../../types';

interface Props {
    visualData: VisualGraph;
}

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

    useEffect(() => {
        if (nodes.length > 0) {
            fitView({ duration: 800 });
        }
    }, [nodes.length, fitView]);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            colorMode="dark"
        >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#ffffff10" />
            <Controls showInteractive={false} className="bg-white/5 border-white/10" />
            <MiniMap
                style={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)' }}
                nodeColor="#333"
                maskColor="rgba(0, 0, 0, 0.3)"
            />
            <Panel position="top-right" className="flex flex-col gap-2">
                <div className="bg-[#0d1117]/80 backdrop-blur-md border border-white/10 rounded-lg p-2 flex items-center gap-3">
                    <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">
                        AWS Dependency Graph
                    </p>
                    <button
                        onClick={toggleFullScreen}
                        className="p-1.5 rounded-md hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                        title={isFullScreen ? "Exit Full Screen" : "Full Screen"}
                    >
                        {isFullScreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                    </button>
                </div>
            </Panel>
        </ReactFlow>
    );
};

export const BlueprintGraph: React.FC<Props> = ({ visualData }) => {
    const [isFullScreen, setIsFullScreen] = useState(false);

    const initialNodes: Node[] = useMemo(() => {
        if (!visualData?.nodes) return [];
        return visualData.nodes.map((node) => ({
            id: node.id,
            position: node.position || { x: 0, y: 0 },
            data: {
                label: node.data?.label || node.id,
                serviceType: node.data?.service_type || 'unknown',
            },
            style: {
                ...(node.style || {}),
                fontSize: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
            },
        }));
    }, [visualData?.nodes]);

    const initialEdges: Edge[] = useMemo(() => {
        if (!visualData?.edges) return [];
        return visualData.edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            animated: edge.animated,
            style: edge.style || {},
            labelStyle: { fill: '#888', fontSize: '8px', fontWeight: 600 },
        }));
    }, [visualData?.edges]);

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    useEffect(() => {
        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [initialNodes, initialEdges, setNodes, setEdges]);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    const toggleFullScreen = () => {
        setIsFullScreen(!isFullScreen);
    };

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

    if (isFullScreen) {
        return (
            <div className="fixed inset-0 z-[9999] bg-[#0d1117] flex flex-col">
                <div className="p-4 border-b border-white/5 flex justify-between items-center bg-[#0d1117]/50 backdrop-blur-xl">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <Share2 size={18} className="text-primary" />
                        </div>
                        <div>
                            <h2 className="text-sm font-bold text-white">Full Screen Blueprint</h2>
                            <p className="text-[11px] text-white/40">AWS Infrastructure Dependency Graph</p>
                        </div>
                    </div>
                    <button
                        onClick={toggleFullScreen}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-white/80 transition-all"
                    >
                        <Minimize2 size={14} />
                        <span>Exit Full Screen</span>
                    </button>
                </div>
                <div className="flex-1">
                    {graphContent}
                </div>
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: '100%', background: '#0d1117', position: 'relative' }}>
            {graphContent}
        </div>
    );
};
