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
    AWS: '#64748b',
};
