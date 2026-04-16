/** @type {import('next').NextConfig} */
const defaultBackendBaseUrl =
  process.env.NODE_ENV === 'production' ? 'http://lerna-backend:8000' : 'http://localhost:8000'
const backendBaseUrl = (process.env.BACKEND_BASE_URL || defaultBackendBaseUrl).replace(/\/$/, '')

const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendBaseUrl}/api/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
