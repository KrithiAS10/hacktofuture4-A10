'use client'
// src/components/charts/SparklineChart.tsx
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { generateTimeSeriesData } from '@/lib/mock-data'
import { useMemo } from 'react'

interface SparklineProps {
  color: string
  gradientId: string
  baseValue?: number
  data?: number[]
  height?: number
  showTooltip?: boolean
  labels?: string[]
}

export function SparklineChart({
  color,
  gradientId,
  baseValue = 60,
  data,
  height = 100,
  showTooltip = false,
  labels,
}: SparklineProps) {
  const values = useMemo(
    () => data ?? generateTimeSeriesData(baseValue, 12, 10),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  )

  const chartData = values.map((v, i) => ({ v, label: labels?.[i] ?? `T-${values.length - i}` }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        {showTooltip && (
          <>
            <XAxis dataKey="label" hide />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                background: '#0D1120',
                border: '1px solid #1E2D45',
                borderRadius: '8px',
                fontSize: '12px',
                fontFamily: 'JetBrains Mono',
                color: '#E8EDF5',
              }}
              formatter={(val: number) => [val.toFixed(1), '']}
              labelStyle={{ color: '#4A5B7A' }}
            />
          </>
        )}
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}