/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  transpilePackages: ["three", "@react-three/fiber", "@react-three/drei"],
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://maitri-fullstack-1.onrender.com',
  },
  allowedDevOrigins: ['pixel-bugs-revealed-findlaw.trycloudflare.com'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')}/api/:path*` : 'https://maitri-fullstack-1.onrender.com/api/:path*',
      },
    ]
  },
}
module.exports = nextConfig
