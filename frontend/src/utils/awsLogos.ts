/**
 * AWS Service logos as inline SVG strings.
 * Each key matches the `type` field returned by the backend tools.
 */

export interface AwsLogoInfo {
    svg: string;
    color: string;    // border/glow accent color
    bg: string;       // icon background color
    category: string;
}

const svgIcon = (content: string) => content;

// ── Logo SVG definitions ─────────────────────────────────────────
// Using AWS-accurate colors and simplified SVG paths

const logos: Record<string, AwsLogoInfo> = {
    // ── Compute ─────────────────────────────────────────────────────
    aws_ec2: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="20" y="20" width="40" height="40" rx="4" fill="none" stroke="#FF9900" stroke-width="3"/>
      <line x1="20" y1="33" x2="60" y2="33" stroke="#FF9900" stroke-width="2"/>
      <line x1="20" y1="47" x2="60" y2="47" stroke="#FF9900" stroke-width="2"/>
      <line x1="33" y1="20" x2="33" y2="60" stroke="#FF9900" stroke-width="2"/>
      <line x1="47" y1="20" x2="47" y2="60" stroke="#FF9900" stroke-width="2"/>
      <circle cx="14" cy="40" r="3" fill="#FF9900"/>
      <circle cx="66" cy="40" r="3" fill="#FF9900"/>
      <circle cx="40" cy="14" r="3" fill="#FF9900"/>
      <circle cx="40" cy="66" r="3" fill="#FF9900"/>
    </svg>`),
    },
    aws_lambda: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <path d="M20 60 L32 28 L40 46 L52 20 L60 60" fill="none" stroke="#FF9900" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M20 60 L36 60" stroke="#FF9900" stroke-width="3" stroke-linecap="round"/>
      <path d="M44 60 L60 60" stroke="#FF9900" stroke-width="3" stroke-linecap="round"/>
    </svg>`),
    },
    aws_ecs: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="16" y="16" width="22" height="22" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <rect x="42" y="16" width="22" height="22" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <rect x="16" y="42" width="22" height="22" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <rect x="42" y="42" width="22" height="22" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
    </svg>`),
    },
    aws_eks: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <polygon points="40,15 63,27.5 63,52.5 40,65 17,52.5 17,27.5" fill="none" stroke="#FF9900" stroke-width="3"/>
      <circle cx="40" cy="40" r="8" fill="#FF9900" opacity="0.8"/>
      <line x1="40" y1="15" x2="40" y2="32" stroke="#FF9900" stroke-width="2"/>
      <line x1="63" y1="27.5" x2="47" y2="36" stroke="#FF9900" stroke-width="2"/>
      <line x1="63" y1="52.5" x2="47" y2="44" stroke="#FF9900" stroke-width="2"/>
      <line x1="40" y1="65" x2="40" y2="48" stroke="#FF9900" stroke-width="2"/>
      <line x1="17" y1="52.5" x2="33" y2="44" stroke="#FF9900" stroke-width="2"/>
      <line x1="17" y1="27.5" x2="33" y2="36" stroke="#FF9900" stroke-width="2"/>
    </svg>`),
    },

    // ── Storage ──────────────────────────────────────────────────────
    aws_s3: {
        color: '#3F8624',
        bg: '#0a1a06',
        category: 'Storage',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#3F8624" opacity="0.15"/>
      <ellipse cx="40" cy="24" rx="22" ry="8" fill="none" stroke="#3F8624" stroke-width="2.5"/>
      <rect x="18" y="24" width="44" height="32" fill="none" stroke="#3F8624" stroke-width="2.5"/>
      <ellipse cx="40" cy="56" rx="22" ry="8" fill="#3F8624" opacity="0.25"/>
      <ellipse cx="40" cy="56" rx="22" ry="8" fill="none" stroke="#3F8624" stroke-width="2.5"/>
      <line x1="18" y1="36" x2="62" y2="36" stroke="#3F8624" stroke-width="1.5" stroke-dasharray="4,3"/>
      <line x1="18" y1="46" x2="62" y2="46" stroke="#3F8624" stroke-width="1.5" stroke-dasharray="4,3"/>
    </svg>`),
    },
    aws_ebs: {
        color: '#3F8624',
        bg: '#0a1a06',
        category: 'Storage',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#3F8624" opacity="0.15"/>
      <rect x="16" y="24" width="48" height="32" rx="4" fill="none" stroke="#3F8624" stroke-width="2.5"/>
      <circle cx="28" cy="40" r="6" fill="none" stroke="#3F8624" stroke-width="2"/>
      <circle cx="52" cy="40" r="6" fill="none" stroke="#3F8624" stroke-width="2"/>
      <circle cx="40" cy="40" r="3" fill="#3F8624"/>
      <line x1="34" y1="40" x2="44" y2="40" stroke="#3F8624" stroke-width="2"/>
    </svg>`),
    },

    // ── Databases ────────────────────────────────────────────────────
    aws_rds: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <ellipse cx="40" cy="26" rx="20" ry="7" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <rect x="20" y="26" width="40" height="28" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="54" rx="20" ry="7" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="38" rx="20" ry="7" fill="none" stroke="#527FFF" stroke-width="1.5" stroke-dasharray="5,3"/>
    </svg>`),
    },
    aws_dynamodb: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <path d="M40 14 C52 14 62 18 62 24 L62 56 C62 62 52 66 40 66 C28 66 18 62 18 56 L18 24 C18 18 28 14 40 14Z" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="24" rx="22" ry="8" fill="none" stroke="#527FFF" stroke-width="2"/>
      <ellipse cx="40" cy="40" rx="22" ry="8" fill="none" stroke="#527FFF" stroke-width="2" stroke-dasharray="5,3"/>
      <path d="M18 24 L18 56" stroke="#527FFF" stroke-width="2.5"/>
      <path d="M62 24 L62 56" stroke="#527FFF" stroke-width="2.5"/>
    </svg>`),
    },
    aws_aurora: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <ellipse cx="40" cy="26" rx="20" ry="7" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <rect x="20" y="26" width="40" height="28" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="54" rx="20" ry="7" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <path d="M32 42 L38 48 L48 34" stroke="#527FFF" stroke-width="3" stroke-linecap="round" fill="none"/>
    </svg>`),
    },
    aws_elasticache: {
        color: '#C7131F',
        bg: '#1a0003',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#C7131F" opacity="0.15"/>
      <circle cx="40" cy="40" r="22" fill="none" stroke="#C7131F" stroke-width="2.5"/>
      <path d="M28 33 Q40 22 52 33 Q40 44 28 33Z" fill="#C7131F" opacity="0.6"/>
      <path d="M28 47 Q40 36 52 47 Q40 58 28 47Z" fill="#C7131F" opacity="0.4"/>
    </svg>`),
    },

    // ── Networking ───────────────────────────────────────────────────
    aws_vpc: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <rect x="14" y="14" width="52" height="52" rx="6" fill="none" stroke="#8C4FFF" stroke-width="2.5" stroke-dasharray="8,4"/>
      <rect x="24" y="24" width="14" height="14" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <rect x="42" y="24" width="14" height="14" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <rect x="24" y="42" width="14" height="14" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <rect x="42" y="42" width="14" height="14" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_elb: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <rect x="14" y="33" width="52" height="14" rx="7" fill="none" stroke="#8C4FFF" stroke-width="2.5"/>
      <circle cx="22" cy="40" r="4" fill="#8C4FFF"/>
      <circle cx="40" cy="40" r="4" fill="#8C4FFF"/>
      <circle cx="58" cy="40" r="4" fill="#8C4FFF"/>
      <line x1="40" y1="22" x2="22" y2="33" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
      <line x1="40" y1="22" x2="40" y2="33" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
      <line x1="40" y1="22" x2="58" y2="33" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
      <line x1="22" y1="47" x2="22" y2="58" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
      <line x1="40" y1="47" x2="40" y2="58" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
      <line x1="58" y1="47" x2="58" y2="58" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="3,2"/>
    </svg>`),
    },
    aws_api_gateway: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <line x1="20" y1="40" x2="60" y2="40" stroke="#E7157B" stroke-width="2"/>
      <path d="M40 20 Q55 30 55 40 Q55 50 40 60" fill="none" stroke="#E7157B" stroke-width="2"/>
      <path d="M40 20 Q25 30 25 40 Q25 50 40 60" fill="none" stroke="#E7157B" stroke-width="2"/>
      <line x1="28" y1="28" x2="52" y2="28" stroke="#E7157B" stroke-width="1.5"/>
      <line x1="28" y1="52" x2="52" y2="52" stroke="#E7157B" stroke-width="1.5"/>
    </svg>`),
    },
    aws_cloudfront: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#8C4FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="40" rx="10" ry="20" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <line x1="20" y1="40" x2="60" y2="40" stroke="#8C4FFF" stroke-width="2"/>
      <path d="M22 30 Q40 24 58 30" fill="none" stroke="#8C4FFF" stroke-width="1.5"/>
      <path d="M22 50 Q40 56 58 50" fill="none" stroke="#8C4FFF" stroke-width="1.5"/>
    </svg>`),
    },
    aws_route53: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#8C4FFF" stroke-width="2.5"/>
      <line x1="20" y1="40" x2="60" y2="40" stroke="#8C4FFF" stroke-width="1.5"/>
      <path d="M40 20 C30 28 30 32 40 40 C50 48 50 52 40 60" fill="none" stroke="#8C4FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_transit_gateway: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="10" fill="#8C4FFF" opacity="0.5"/>
      <circle cx="40" cy="40" r="10" fill="none" stroke="#8C4FFF" stroke-width="2.5"/>
      <line x1="40" y1="20" x2="40" y2="30" stroke="#8C4FFF" stroke-width="2.5"/>
      <line x1="60" y1="40" x2="50" y2="40" stroke="#8C4FFF" stroke-width="2.5"/>
      <line x1="40" y1="60" x2="40" y2="50" stroke="#8C4FFF" stroke-width="2.5"/>
      <line x1="20" y1="40" x2="30" y2="40" stroke="#8C4FFF" stroke-width="2.5"/>
      <circle cx="40" cy="17" r="4" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <circle cx="63" cy="40" r="4" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <circle cx="40" cy="63" r="4" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <circle cx="17" cy="40" r="4" fill="none" stroke="#8C4FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_nat_gateway: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <path d="M40 18 L62 58 L18 58 Z" fill="none" stroke="#8C4FFF" stroke-width="2.5" stroke-linejoin="round"/>
      <circle cx="40" cy="50" r="3" fill="#8C4FFF"/>
      <line x1="40" y1="32" x2="40" y2="44" stroke="#8C4FFF" stroke-width="3" stroke-linecap="round"/>
    </svg>`),
    },

    // ── Messaging ────────────────────────────────────────────────────
    aws_sqs: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Messaging',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <rect x="14" y="28" width="52" height="24" rx="4" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <line x1="24" y1="36" x2="36" y2="36" stroke="#E7157B" stroke-width="2" stroke-linecap="round"/>
      <line x1="24" y1="40" x2="56" y2="40" stroke="#E7157B" stroke-width="2" stroke-linecap="round"/>
      <line x1="24" y1="44" x2="46" y2="44" stroke="#E7157B" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },
    aws_sns: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Messaging',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <circle cx="40" cy="32" r="10" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <path d="M18 58 Q30 50 40 52 Q50 54 62 48" fill="none" stroke="#E7157B" stroke-width="2" stroke-linecap="round"/>
      <line x1="32" y1="42" x2="26" y2="54" stroke="#E7157B" stroke-width="2"/>
      <line x1="48" y1="42" x2="54" y2="54" stroke="#E7157B" stroke-width="2"/>
      <path d="M30 28 Q40 18 50 28" fill="none" stroke="#E7157B" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },
    aws_eventbridge: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Messaging',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <circle cx="40" cy="40" r="18" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <path d="M36 28 L44 40 L36 52" fill="none" stroke="#E7157B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="22" y1="40" x2="36" y2="40" stroke="#E7157B" stroke-width="2.5"/>
      <line x1="44" y1="40" x2="56" y2="40" stroke="#E7157B" stroke-width="2" stroke-dasharray="3,2"/>
    </svg>`),
    },
    aws_kinesis: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Messaging',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <path d="M18 52 Q28 30 40 40 Q52 50 62 28" fill="none" stroke="#E7157B" stroke-width="3" stroke-linecap="round"/>
      <circle cx="18" cy="52" r="4" fill="#E7157B"/>
      <circle cx="62" cy="28" r="4" fill="#E7157B"/>
    </svg>`),
    },

    // ── Security ─────────────────────────────────────────────────────
    aws_iam: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <path d="M40 14 L58 22 L58 40 C58 52 50 62 40 66 C30 62 22 52 22 40 L22 22 Z" fill="none" stroke="#DD344C" stroke-width="2.5" stroke-linejoin="round"/>
      <circle cx="40" cy="36" r="7" fill="none" stroke="#DD344C" stroke-width="2"/>
      <path d="M28 54 C28 46 52 46 52 54" fill="none" stroke="#DD344C" stroke-width="2"/>
    </svg>`),
    },
    aws_cognito: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <circle cx="40" cy="32" r="12" fill="none" stroke="#DD344C" stroke-width="2.5"/>
      <path d="M20 62 C20 50 60 50 60 62" fill="none" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="40" cy="32" r="5" fill="#DD344C" opacity="0.6"/>
    </svg>`),
    },
    aws_secrets_manager: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <rect x="24" y="36" width="32" height="26" rx="4" fill="none" stroke="#DD344C" stroke-width="2.5"/>
      <path d="M30 36 L30 28 C30 20 50 20 50 28 L50 36" fill="none" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="40" cy="49" r="4" fill="#DD344C"/>
      <line x1="40" y1="53" x2="40" y2="58" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
    </svg>`),
    },

    // ── Monitoring ───────────────────────────────────────────────────
    aws_cloudwatch: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Monitoring',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <circle cx="40" cy="40" r="22" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <polyline points="22,48 30,38 38,32 46,42 54,28 62,34" fill="none" stroke="#E7157B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`),
    },

    // ── DevOps ───────────────────────────────────────────────────────
    aws_ecr: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'DevOps',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="18" y="20" width="44" height="40" rx="4" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <line x1="18" y1="32" x2="62" y2="32" stroke="#FF9900" stroke-width="2"/>
      <circle cx="27" cy="26" r="2.5" fill="#FF9900"/>
      <circle cx="35" cy="26" r="2.5" fill="#FF9900"/>
      <circle cx="43" cy="26" r="2.5" fill="#FF9900"/>
      <path d="M28 44 L36 44 L36 52 L28 52 Z" fill="none" stroke="#FF9900" stroke-width="2"/>
      <path d="M40 44 L52 44" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <path d="M40 48.5 L48 48.5" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },

    // ── Analytics ────────────────────────────────────────────────────
    aws_redshift: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="10" fill="#527FFF" opacity="0.3"/>
      <line x1="40" y1="20" x2="40" y2="28" stroke="#527FFF" stroke-width="2"/>
      <line x1="40" y1="52" x2="40" y2="60" stroke="#527FFF" stroke-width="2"/>
      <line x1="20" y1="40" x2="28" y2="40" stroke="#527FFF" stroke-width="2"/>
      <line x1="52" y1="40" x2="60" y2="40" stroke="#527FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_glue: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="22" cy="28" r="6" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="58" cy="28" r="6" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="22" cy="52" r="6" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="58" cy="52" r="6" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="8" fill="#527FFF" opacity="0.4"/>
      <circle cx="40" cy="40" r="8" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <line x1="28" y1="31" x2="33" y2="36" stroke="#527FFF" stroke-width="2"/>
      <line x1="52" y1="31" x2="47" y2="36" stroke="#527FFF" stroke-width="2"/>
      <line x1="28" y1="49" x2="33" y2="44" stroke="#527FFF" stroke-width="2"/>
      <line x1="52" y1="49" x2="47" y2="44" stroke="#527FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_athena: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="36" cy="36" r="16" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <line x1="48" y1="48" x2="62" y2="62" stroke="#527FFF" stroke-width="3.5" stroke-linecap="round"/>
      <line x1="28" y1="36" x2="44" y2="36" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <line x1="30" y1="30" x2="42" y2="30" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <line x1="30" y1="42" x2="40" y2="42" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },
    aws_emr: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="14" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <circle cx="18" cy="30" r="6" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="62" cy="30" r="6" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="18" cy="50" r="6" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="62" cy="50" r="6" fill="none" stroke="#527FFF" stroke-width="2"/>
      <line x1="24" y1="32" x2="28" y2="35" stroke="#527FFF" stroke-width="2"/>
      <line x1="56" y1="32" x2="52" y2="35" stroke="#527FFF" stroke-width="2"/>
      <line x1="24" y1="48" x2="28" y2="45" stroke="#527FFF" stroke-width="2"/>
      <line x1="56" y1="48" x2="52" y2="45" stroke="#527FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_opensearch: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="35" cy="35" r="17" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <line x1="47" y1="47" x2="63" y2="63" stroke="#527FFF" stroke-width="3.5" stroke-linecap="round"/>
      <path d="M27 35 Q35 24 43 35" fill="none" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <path d="M27 35 Q35 46 43 35" fill="none" stroke="#527FFF" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`),
    },
    aws_msk: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Analytics',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <rect x="16" y="26" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="16" y="42" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="34" y="18" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="34" y="34" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="34" y="50" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="52" y="26" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <rect x="52" y="42" width="12" height="12" rx="2" fill="none" stroke="#527FFF" stroke-width="2"/>
      <line x1="28" y1="32" x2="34" y2="24" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="28" y1="32" x2="34" y2="40" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="28" y1="48" x2="34" y2="40" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="28" y1="48" x2="34" y2="56" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="46" y1="24" x2="52" y2="32" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="46" y1="40" x2="52" y2="32" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="46" y1="40" x2="52" y2="48" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="46" y1="56" x2="52" y2="48" stroke="#527FFF" stroke-width="1.5"/>
    </svg>`),
    },

    // ── Additional Compute ───────────────────────────────────────────
    aws_app_runner: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="18" y="22" width="44" height="36" rx="5" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <polygon points="34,32 34,48 54,40" fill="#FF9900" opacity="0.8"/>
    </svg>`),
    },
    aws_step_functions: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="24" y="14" width="16" height="10" rx="3" fill="none" stroke="#FF9900" stroke-width="2"/>
      <rect x="40" y="35" width="16" height="10" rx="3" fill="none" stroke="#FF9900" stroke-width="2"/>
      <rect x="24" y="56" width="16" height="10" rx="3" fill="none" stroke="#FF9900" stroke-width="2"/>
      <line x1="32" y1="24" x2="32" y2="32" stroke="#FF9900" stroke-width="2"/>
      <line x1="32" y1="32" x2="48" y2="32" stroke="#FF9900" stroke-width="2"/>
      <line x1="48" y1="32" x2="48" y2="35" stroke="#FF9900" stroke-width="2"/>
      <line x1="48" y1="45" x2="48" y2="52" stroke="#FF9900" stroke-width="2"/>
      <line x1="48" y1="52" x2="32" y2="52" stroke="#FF9900" stroke-width="2"/>
      <line x1="32" y1="52" x2="32" y2="56" stroke="#FF9900" stroke-width="2"/>
    </svg>`),
    },
    aws_batch: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="16" y="48" width="48" height="14" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <rect x="16" y="33" width="48" height="14" rx="3" fill="none" stroke="#FF9900" stroke-width="2"/>
      <rect x="16" y="18" width="48" height="14" rx="3" fill="none" stroke="#FF9900" stroke-width="1.5" stroke-dasharray="4,3"/>
      <circle cx="28" cy="55" r="3" fill="#FF9900"/>
      <circle cx="28" cy="40" r="3" fill="#FF9900" opacity="0.6"/>
    </svg>`),
    },
    aws_elastic_beanstalk: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <ellipse cx="40" cy="44" rx="18" ry="12" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <line x1="40" y1="32" x2="40" y2="18" stroke="#FF9900" stroke-width="2.5"/>
      <path d="M32 24 Q40 14 48 24" fill="none" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <circle cx="40" cy="15" r="3.5" fill="#FF9900"/>
      <line x1="24" y1="50" x2="18" y2="60" stroke="#FF9900" stroke-width="2"/>
      <line x1="56" y1="50" x2="62" y2="60" stroke="#FF9900" stroke-width="2"/>
    </svg>`),
    },
    aws_lightsail: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'Compute',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <circle cx="40" cy="38" r="12" fill="#FF9900" opacity="0.3"/>
      <circle cx="40" cy="38" r="12" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <line x1="40" y1="16" x2="40" y2="22" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="40" y1="54" x2="40" y2="60" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="18" y1="38" x2="24" y2="38" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="56" y1="38" x2="62" y2="38" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="24" y1="24" x2="28" y2="28" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <line x1="52" y1="48" x2="56" y2="52" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <line x1="56" y1="24" x2="52" y2="28" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <line x1="28" y1="48" x2="24" y2="52" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
      <path d="M34 62 Q40 66 46 62" fill="none" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },

    // ── Additional Storage ───────────────────────────────────────────
    aws_efs: {
        color: '#3F8624',
        bg: '#0a1a06',
        category: 'Storage',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#3F8624" opacity="0.15"/>
      <rect x="18" y="22" width="20" height="26" rx="3" fill="none" stroke="#3F8624" stroke-width="2"/>
      <rect x="42" y="22" width="20" height="26" rx="3" fill="none" stroke="#3F8624" stroke-width="2"/>
      <line x1="38" y1="35" x2="42" y2="35" stroke="#3F8624" stroke-width="2.5"/>
      <line x1="24" y1="28" x2="32" y2="28" stroke="#3F8624" stroke-width="1.5"/>
      <line x1="24" y1="32" x2="32" y2="32" stroke="#3F8624" stroke-width="1.5"/>
      <line x1="48" y1="28" x2="56" y2="28" stroke="#3F8624" stroke-width="1.5"/>
      <line x1="48" y1="32" x2="56" y2="32" stroke="#3F8624" stroke-width="1.5"/>
      <path d="M20 52 Q40 60 60 52" fill="none" stroke="#3F8624" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },
    aws_fsx: {
        color: '#3F8624',
        bg: '#0a1a06',
        category: 'Storage',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#3F8624" opacity="0.15"/>
      <rect x="16" y="20" width="48" height="16" rx="3" fill="none" stroke="#3F8624" stroke-width="2.5"/>
      <rect x="16" y="44" width="48" height="16" rx="3" fill="none" stroke="#3F8624" stroke-width="2"/>
      <line x1="26" y1="28" x2="54" y2="28" stroke="#3F8624" stroke-width="2" stroke-linecap="round"/>
      <line x1="26" y1="52" x2="46" y2="52" stroke="#3F8624" stroke-width="2" stroke-linecap="round"/>
      <line x1="40" y1="36" x2="40" y2="44" stroke="#3F8624" stroke-width="2.5"/>
      <polygon points="36,40 44,40 40,44" fill="#3F8624"/>
    </svg>`),
    },
    aws_glacier: {
        color: '#3F8624',
        bg: '#0a1a06',
        category: 'Storage',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#3F8624" opacity="0.15"/>
      <polygon points="40,16 66,60 14,60" fill="#3F8624" opacity="0.2"/>
      <polygon points="40,16 66,60 14,60" fill="none" stroke="#3F8624" stroke-width="2.5" stroke-linejoin="round"/>
      <polygon points="40,30 52,52 28,52" fill="#3F8624" opacity="0.4"/>
      <line x1="20" y1="60" x2="60" y2="60" stroke="#3F8624" stroke-width="3" stroke-linecap="round"/>
    </svg>`),
    },

    // ── Additional Database ──────────────────────────────────────────
    aws_neptune: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="7" fill="#527FFF" opacity="0.5"/>
      <circle cx="20" cy="26" r="5" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="60" cy="26" r="5" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="20" cy="54" r="5" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="60" cy="54" r="5" fill="none" stroke="#527FFF" stroke-width="2"/>
      <circle cx="40" cy="16" r="5" fill="none" stroke="#527FFF" stroke-width="2"/>
      <line x1="40" y1="21" x2="40" y2="33" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="24" y1="27" x2="34" y2="36" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="56" y1="27" x2="46" y2="36" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="24" y1="53" x2="34" y2="44" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="56" y1="53" x2="46" y2="44" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="20" y1="31" x2="20" y2="49" stroke="#527FFF" stroke-width="1.5"/>
      <line x1="60" y1="31" x2="60" y2="49" stroke="#527FFF" stroke-width="1.5"/>
    </svg>`),
    },
    aws_documentdb: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <rect x="22" y="18" width="28" height="36" rx="2" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <line x1="28" y1="26" x2="44" y2="26" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <line x1="28" y1="32" x2="44" y2="32" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <line x1="28" y1="38" x2="38" y2="38" stroke="#527FFF" stroke-width="2" stroke-linecap="round"/>
      <rect x="30" y="24" width="28" height="36" rx="2" fill="none" stroke="#527FFF" stroke-width="1.5" stroke-dasharray="4,3"/>
    </svg>`),
    },
    aws_timestream: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <polyline points="14,56 24,44 32,50 40,32 50,38 58,22 66,28" fill="none" stroke="#527FFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="14" y1="60" x2="66" y2="60" stroke="#527FFF" stroke-width="1.5"/>
      <circle cx="40" cy="32" r="3.5" fill="#527FFF"/>
    </svg>`),
    },
    aws_keyspaces: {
        color: '#527FFF',
        bg: '#06093a',
        category: 'Database',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#527FFF" opacity="0.15"/>
      <circle cx="30" cy="34" r="10" fill="none" stroke="#527FFF" stroke-width="2.5"/>
      <line x1="37" y1="41" x2="64" y2="56" stroke="#527FFF" stroke-width="3" stroke-linecap="round"/>
      <line x1="50" y1="46" x2="50" y2="52" stroke="#527FFF" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="57" y1="50" x2="57" y2="56" stroke="#527FFF" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="30" cy="34" r="4" fill="#527FFF" opacity="0.5"/>
    </svg>`),
    },

    // ── Additional Networking ────────────────────────────────────────
    aws_security_group: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <path d="M40 14 L58 22 L58 42 C58 54 50 62 40 66 C30 62 22 54 22 42 L22 22 Z" fill="none" stroke="#8C4FFF" stroke-width="2.5" stroke-linejoin="round"/>
      <line x1="30" y1="40" x2="50" y2="40" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="5,3"/>
      <line x1="30" y1="46" x2="50" y2="46" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="5,3"/>
      <line x1="30" y1="34" x2="50" y2="34" stroke="#8C4FFF" stroke-width="2"/>
    </svg>`),
    },
    aws_global_accelerator: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#8C4FFF" stroke-width="2.5"/>
      <ellipse cx="40" cy="40" rx="10" ry="20" fill="none" stroke="#8C4FFF" stroke-width="1.5"/>
      <line x1="20" y1="40" x2="60" y2="40" stroke="#8C4FFF" stroke-width="1.5"/>
      <polygon points="44,32 44,48 58,40" fill="#8C4FFF" opacity="0.7"/>
    </svg>`),
    },
    aws_vpn_gateway: {
        color: '#8C4FFF',
        bg: '#0f0a1a',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#8C4FFF" opacity="0.15"/>
      <rect x="14" y="30" width="20" height="20" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <rect x="46" y="30" width="20" height="20" rx="3" fill="none" stroke="#8C4FFF" stroke-width="2"/>
      <line x1="34" y1="38" x2="46" y2="38" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="4,3"/>
      <line x1="34" y1="42" x2="46" y2="42" stroke="#8C4FFF" stroke-width="2" stroke-dasharray="4,3"/>
      <rect x="24" y="36" width="12" height="8" rx="2" fill="#8C4FFF" opacity="0.4"/>
      <rect x="44" y="36" width="12" height="8" rx="2" fill="#8C4FFF" opacity="0.4"/>
    </svg>`),
    },
    aws_apigatewayv2: {
        color: '#E7157B',
        bg: '#1a0010',
        category: 'Networking',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#E7157B" opacity="0.15"/>
      <circle cx="40" cy="40" r="20" fill="none" stroke="#E7157B" stroke-width="2.5"/>
      <line x1="20" y1="40" x2="60" y2="40" stroke="#E7157B" stroke-width="2"/>
      <path d="M40 20 Q55 30 55 40 Q55 50 40 60" fill="none" stroke="#E7157B" stroke-width="2"/>
      <path d="M40 20 Q25 30 25 40 Q25 50 40 60" fill="none" stroke="#E7157B" stroke-width="2"/>
      <text x="32" y="44" font-size="10" fill="#E7157B" font-weight="bold">v2</text>
    </svg>`),
    },

    // ── Additional Security ──────────────────────────────────────────
    aws_kms: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <circle cx="32" cy="34" r="12" fill="none" stroke="#DD344C" stroke-width="2.5"/>
      <line x1="41" y1="43" x2="66" y2="60" stroke="#DD344C" stroke-width="3" stroke-linecap="round"/>
      <line x1="53" y1="49" x2="53" y2="55" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="60" y1="54" x2="60" y2="60" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="32" cy="34" r="5" fill="#DD344C" opacity="0.5"/>
    </svg>`),
    },
    aws_waf: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <path d="M40 14 L58 22 L58 40 C58 52 50 62 40 66 C30 62 22 52 22 40 L22 22 Z" fill="none" stroke="#DD344C" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M32 40 L38 46 L50 32" stroke="#DD344C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>`),
    },
    aws_guardduty: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <circle cx="40" cy="40" r="18" fill="none" stroke="#DD344C" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="8" fill="none" stroke="#DD344C" stroke-width="2"/>
      <circle cx="40" cy="40" r="3" fill="#DD344C"/>
      <line x1="22" y1="26" x2="30" y2="34" stroke="#DD344C" stroke-width="2"/>
      <line x1="58" y1="26" x2="50" y2="34" stroke="#DD344C" stroke-width="2"/>
    </svg>`),
    },
    aws_acm: {
        color: '#DD344C',
        bg: '#1a0007',
        category: 'Security',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#DD344C" opacity="0.15"/>
      <rect x="18" y="18" width="44" height="34" rx="4" fill="none" stroke="#DD344C" stroke-width="2.5"/>
      <circle cx="40" cy="34" r="8" fill="none" stroke="#DD344C" stroke-width="2"/>
      <line x1="36" y1="52" x2="34" y2="64" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="44" y1="52" x2="46" y2="64" stroke="#DD344C" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="30" y1="62" x2="50" y2="62" stroke="#DD344C" stroke-width="2" stroke-linecap="round"/>
      <circle cx="40" cy="34" r="3" fill="#DD344C" opacity="0.6"/>
    </svg>`),
    },

    // ── Additional DevOps ────────────────────────────────────────────
    aws_codepipeline: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'DevOps',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <circle cx="16" cy="40" r="6" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="6" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <circle cx="64" cy="40" r="6" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <line x1="22" y1="40" x2="34" y2="40" stroke="#FF9900" stroke-width="2.5"/>
      <line x1="46" y1="40" x2="58" y2="40" stroke="#FF9900" stroke-width="2.5"/>
      <polygon points="34,36 34,44 40,40" fill="#FF9900"/>
      <polygon points="58,36 58,44 64,40" fill="#FF9900"/>
    </svg>`),
    },
    aws_codebuild: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'DevOps',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <circle cx="40" cy="40" r="18" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <path d="M34 33 L28 40 L34 47" fill="none" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M46 33 L52 40 L46 47" fill="none" stroke="#FF9900" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="42" y1="30" x2="38" y2="50" stroke="#FF9900" stroke-width="2" stroke-linecap="round"/>
    </svg>`),
    },
    aws_cloudformation: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'DevOps',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <rect x="16" y="52" width="48" height="12" rx="3" fill="none" stroke="#FF9900" stroke-width="2.5"/>
      <rect x="22" y="38" width="36" height="12" rx="3" fill="none" stroke="#FF9900" stroke-width="2"/>
      <rect x="28" y="24" width="24" height="12" rx="3" fill="none" stroke="#FF9900" stroke-width="1.5" stroke-dasharray="4,3"/>
      <line x1="40" y1="36" x2="40" y2="38" stroke="#FF9900" stroke-width="2"/>
      <line x1="40" y1="50" x2="40" y2="52" stroke="#FF9900" stroke-width="2"/>
    </svg>`),
    },
    aws_amplify: {
        color: '#FF9900',
        bg: '#1a1200',
        category: 'DevOps',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#FF9900" opacity="0.15"/>
      <path d="M40 16 L16 62 L40 54 L64 62 Z" fill="#FF9900" opacity="0.2"/>
      <path d="M40 16 L16 62 L40 54 L64 62 Z" fill="none" stroke="#FF9900" stroke-width="2.5" stroke-linejoin="round"/>
      <line x1="40" y1="16" x2="40" y2="54" stroke="#FF9900" stroke-width="2"/>
    </svg>`),
    },

    // ── AI/ML ────────────────────────────────────────────────────────
    aws_sagemaker: {
        color: '#00A4A6',
        bg: '#001a1a',
        category: 'AI/ML',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#00A4A6" opacity="0.15"/>
      <circle cx="26" cy="30" r="8" fill="none" stroke="#00A4A6" stroke-width="2.5"/>
      <circle cx="54" cy="30" r="8" fill="none" stroke="#00A4A6" stroke-width="2.5"/>
      <circle cx="40" cy="54" r="8" fill="none" stroke="#00A4A6" stroke-width="2.5"/>
      <line x1="34" y1="30" x2="46" y2="30" stroke="#00A4A6" stroke-width="2"/>
      <line x1="30" y1="37" x2="36" y2="47" stroke="#00A4A6" stroke-width="2"/>
      <line x1="50" y1="37" x2="44" y2="47" stroke="#00A4A6" stroke-width="2"/>
      <circle cx="26" cy="30" r="3" fill="#00A4A6" opacity="0.7"/>
      <circle cx="54" cy="30" r="3" fill="#00A4A6" opacity="0.7"/>
      <circle cx="40" cy="54" r="3" fill="#00A4A6" opacity="0.7"/>
    </svg>`),
    },
    aws_bedrock: {
        color: '#00A4A6',
        bg: '#001a1a',
        category: 'AI/ML',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#00A4A6" opacity="0.15"/>
      <rect x="16" y="54" width="48" height="10" rx="2" fill="#00A4A6" opacity="0.4"/>
      <rect x="16" y="54" width="48" height="10" rx="2" fill="none" stroke="#00A4A6" stroke-width="2"/>
      <rect x="20" y="42" width="40" height="10" rx="2" fill="#00A4A6" opacity="0.3"/>
      <rect x="20" y="42" width="40" height="10" rx="2" fill="none" stroke="#00A4A6" stroke-width="2"/>
      <rect x="24" y="30" width="32" height="10" rx="2" fill="#00A4A6" opacity="0.2"/>
      <rect x="24" y="30" width="32" height="10" rx="2" fill="none" stroke="#00A4A6" stroke-width="2"/>
      <rect x="28" y="18" width="24" height="10" rx="2" fill="none" stroke="#00A4A6" stroke-width="2" stroke-dasharray="4,3"/>
    </svg>`),
    },
    aws_rekognition: {
        color: '#00A4A6',
        bg: '#001a1a',
        category: 'AI/ML',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#00A4A6" opacity="0.15"/>
      <rect x="16" y="22" width="48" height="36" rx="4" fill="none" stroke="#00A4A6" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="10" fill="none" stroke="#00A4A6" stroke-width="2"/>
      <circle cx="40" cy="40" r="4" fill="#00A4A6" opacity="0.6"/>
      <line x1="16" y1="30" x2="26" y2="30" stroke="#00A4A6" stroke-width="2"/>
      <line x1="16" y1="50" x2="26" y2="50" stroke="#00A4A6" stroke-width="2"/>
      <line x1="54" y1="30" x2="64" y2="30" stroke="#00A4A6" stroke-width="2"/>
      <line x1="54" y1="50" x2="64" y2="50" stroke="#00A4A6" stroke-width="2"/>
    </svg>`),
    },
    aws_comprehend: {
        color: '#00A4A6',
        bg: '#001a1a',
        category: 'AI/ML',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#00A4A6" opacity="0.15"/>
      <rect x="16" y="20" width="48" height="40" rx="4" fill="none" stroke="#00A4A6" stroke-width="2.5"/>
      <line x1="24" y1="30" x2="56" y2="30" stroke="#00A4A6" stroke-width="2" stroke-linecap="round"/>
      <line x1="24" y1="37" x2="56" y2="37" stroke="#00A4A6" stroke-width="2" stroke-linecap="round"/>
      <line x1="24" y1="44" x2="44" y2="44" stroke="#00A4A6" stroke-width="2" stroke-linecap="round"/>
      <circle cx="52" cy="52" r="8" fill="none" stroke="#00A4A6" stroke-width="2"/>
      <path d="M48 52 Q52 46 56 52" fill="none" stroke="#00A4A6" stroke-width="1.5"/>
    </svg>`),
    },

    // ── Application ──────────────────────────────────────────────────
    aws_appsync: {
        color: '#C7131F',
        bg: '#1a0003',
        category: 'Application',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#C7131F" opacity="0.15"/>
      <polygon points="40,18 54,26 54,42 40,50 26,42 26,26" fill="none" stroke="#C7131F" stroke-width="2.5"/>
      <line x1="40" y1="18" x2="40" y2="50" stroke="#C7131F" stroke-width="1.5"/>
      <line x1="26" y1="26" x2="54" y2="42" stroke="#C7131F" stroke-width="1.5"/>
      <line x1="54" y1="26" x2="26" y2="42" stroke="#C7131F" stroke-width="1.5"/>
      <circle cx="40" cy="60" r="5" fill="none" stroke="#C7131F" stroke-width="2"/>
      <line x1="40" y1="50" x2="40" y2="55" stroke="#C7131F" stroke-width="2"/>
    </svg>`),
    },
    aws_ses: {
        color: '#C7131F',
        bg: '#1a0003',
        category: 'Application',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#C7131F" opacity="0.15"/>
      <rect x="14" y="24" width="52" height="36" rx="4" fill="none" stroke="#C7131F" stroke-width="2.5"/>
      <path d="M14 28 L40 46 L66 28" fill="none" stroke="#C7131F" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="14" y1="52" x2="30" y2="40" stroke="#C7131F" stroke-width="1.5"/>
      <line x1="66" y1="52" x2="50" y2="40" stroke="#C7131F" stroke-width="1.5"/>
    </svg>`),
    },
    aws_pinpoint: {
        color: '#C7131F',
        bg: '#1a0003',
        category: 'Application',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#C7131F" opacity="0.15"/>
      <path d="M40 18 C28 18 20 26 20 36 C20 50 40 64 40 64 C40 64 60 50 60 36 C60 26 52 18 40 18Z" fill="none" stroke="#C7131F" stroke-width="2.5"/>
      <circle cx="40" cy="36" r="8" fill="#C7131F" opacity="0.4"/>
      <circle cx="40" cy="36" r="8" fill="none" stroke="#C7131F" stroke-width="2"/>
    </svg>`),
    },
    aws_iot_core: {
        color: '#C7131F',
        bg: '#1a0003',
        category: 'Application',
        svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="12" fill="#C7131F" opacity="0.15"/>
      <rect x="30" y="30" width="20" height="20" rx="3" fill="none" stroke="#C7131F" stroke-width="2.5"/>
      <circle cx="40" cy="40" r="5" fill="#C7131F" opacity="0.5"/>
      <path d="M24 26 Q18 32 18 40 Q18 48 24 54" fill="none" stroke="#C7131F" stroke-width="2" stroke-linecap="round"/>
      <path d="M56 26 Q62 32 62 40 Q62 48 56 54" fill="none" stroke="#C7131F" stroke-width="2" stroke-linecap="round"/>
      <path d="M18 20 Q10 28 10 40 Q10 52 18 60" fill="none" stroke="#C7131F" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M62 20 Q70 28 70 40 Q70 52 62 60" fill="none" stroke="#C7131F" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`),
    },
};

// Fallback logo for unknown service types
const fallbackLogo: AwsLogoInfo = {
    color: '#64748b',
    bg: '#0d1117',
    category: 'AWS',
    svg: svgIcon(`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
    <rect width="80" height="80" rx="12" fill="#64748b" opacity="0.15"/>
    <path d="M20 50 Q20 30 40 26 Q60 30 60 50" fill="none" stroke="#64748b" stroke-width="2.5" stroke-linecap="round"/>
    <rect x="22" y="46" width="36" height="14" rx="3" fill="none" stroke="#64748b" stroke-width="2.5"/>
    <circle cx="32" cy="53" r="3" fill="#64748b" opacity="0.6"/>
    <circle cx="48" cy="53" r="3" fill="#64748b" opacity="0.6"/>
  </svg>`),
};

export function getAwsLogo(serviceType: string): AwsLogoInfo {
    const normalizedType = serviceType?.toLowerCase().replace(/-/g, '_') || '';

    // Direct match
    if (logos[normalizedType]) return logos[normalizedType];

    // Partial match (e.g. "ec2_instance" → "aws_ec2")
    for (const [key, logo] of Object.entries(logos)) {
        const cleanKey = key.replace('aws_', '');
        if (normalizedType.includes(cleanKey) || cleanKey.includes(normalizedType)) {
            return logo;
        }
    }

    return fallbackLogo;
}

export const categoryColors: Record<string, string> = {
    Compute: '#FF9900',
    Storage: '#3F8624',
    Database: '#527FFF',
    Networking: '#8C4FFF',
    Messaging: '#E7157B',
    Security: '#DD344C',
    Monitoring: '#E7157B',
    DevOps: '#FF9900',
    Analytics: '#527FFF',
    'AI/ML': '#00A4A6',
    Application: '#C7131F',
    AWS: '#64748b',
};
