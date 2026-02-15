export interface UserPreferences {
    default_region: string;
    default_vpc: boolean;
    naming_convention: string;
    tags: Record<string, string>;
}

export interface User {
    id: number;
    email: string;
    preferences?: UserPreferences;
    created_at?: string;
}

export interface UserLogin {
    email: string;
    password: string;
}

export interface UserCreate {
    email: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

export interface ProjectResponse {
    id: number;
    name: string;
    description?: string;
    status: string;
    region: string;
    natural_language_input?: string;
    created_at?: string;
    updated_at?: string;
}

export type Project = ProjectResponse;

export interface ProjectCreate {
    name: string;
    description?: string;
    region?: string;
    natural_language_input?: string;
}

export interface IntentOutput {
    app_type: string;
    scale: string;
    latency_requirement: string;
    storage_type: string;
    realtime: boolean;
    constraints: string[];
}

export interface NodeConfig {
    runtime?: string;
    memory?: number;
    instance_type?: string;
    engine?: string;
    capacity?: string;
    extra?: Record<string, string>;
}

export interface ArchitectureNode {
    id: string;
    type: string;
    label: string;
    config: NodeConfig;
}

export interface ArchitectureEdge {
    source: string;
    target: string;
    label: string;
}

export interface ArchitectureGraph {
    nodes: ArchitectureNode[];
    edges: ArchitectureEdge[];
}

export interface TerraformFileMap {
    files: Record<string, string>;
}

export interface CostBreakdown {
    service: string;
    estimated_monthly_cost: number;
    details: string;
}

export interface CostEstimate {
    estimated_monthly_cost: number;
    currency: string;
    breakdown: CostBreakdown[];
}

export interface VisualNode {
    id: string;
    type: string;
    position: { x: number; y: number };
    data: Record<string, any>;
    style: Record<string, any>;
}

export interface VisualEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    animated: boolean;
    style: Record<string, any>;
}

export interface VisualGraph {
    nodes: VisualNode[];
    edges: VisualEdge[];
}

export interface ArchitectureResponse {
    id: number;
    project_id: number;
    version: number;
    intent: IntentOutput;
    graph: ArchitectureGraph;
    terraform_files?: TerraformFileMap;
    cost?: CostEstimate;
    visual?: VisualGraph;
}

export interface DeploymentResponse {
    id: number;
    project_id: number;
    architecture_version: number;
    action: string;
    status: string;
    logs?: string;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
    created_at?: string;
}
