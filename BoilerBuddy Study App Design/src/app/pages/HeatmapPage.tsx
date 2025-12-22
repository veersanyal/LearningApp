import { useState } from 'react';
import { motion } from 'motion/react';
import { MapPin, Clock, Users } from 'lucide-react';

const studyLocations = [
  { id: 1, name: 'Hicks Undergraduate Library', x: 35, y: 45, students: 24, hot: true },
  { id: 2, name: 'PMU Study Rooms', x: 55, y: 30, students: 18, hot: true },
  { id: 3, name: 'WALC', x: 70, y: 55, students: 32, hot: true },
  { id: 4, name: 'MATH Building', x: 25, y: 65, students: 15, hot: false },
  { id: 5, name: 'Engineering Fountain', x: 45, y: 70, students: 8, hot: false },
  { id: 6, name: 'Krannert', x: 60, y: 50, students: 12, hot: false },
  { id: 7, name: 'LILY Hall', x: 40, y: 35, students: 6, hot: false },
];

export function HeatmapPage() {
  const [timeFilter, setTimeFilter] = useState('now');
  const [hoveredLocation, setHoveredLocation] = useState<number | null>(null);

  const getHeatIntensity = (students: number) => {
    if (students > 25) return 'from-red-500 to-orange-500';
    if (students > 15) return 'from-orange-500 to-yellow-500';
    return 'from-yellow-500 to-green-500';
  };

  const getMarkerSize = (students: number) => {
    if (students > 25) return 'w-20 h-20';
    if (students > 15) return 'w-16 h-16';
    return 'w-12 h-12';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-4 md:p-6 lg:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl mb-2 flex items-center gap-3">
            <MapPin className="w-8 h-8 text-purple-600" />
            Campus Heatmap
          </h1>
          <p className="text-gray-600">See where Boilermakers are studying right now</p>
        </div>

        {/* Time Filter */}
        <div className="bg-white rounded-2xl p-4 md:p-6 shadow-sm border border-gray-100 mb-6">
          <label className="text-sm text-gray-600 mb-3 block flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Time Filter
          </label>

          <div className="flex gap-2">
            {['now', '24h', 'week'].map((filter) => (
              <button
                key={filter}
                onClick={() => setTimeFilter(filter)}
                className={`px-4 py-2 rounded-xl transition-all ${
                  timeFilter === filter
                    ? 'bg-purple-100 text-purple-900 border-2 border-purple-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filter === 'now' ? 'Now' : filter === '24h' ? 'Past 24 Hours' : 'Past Week'}
              </button>
            ))}
          </div>
        </div>

        {/* Heatmap */}
        <div className="bg-white rounded-3xl p-6 md:p-8 shadow-lg border border-gray-100 mb-6">
          {/* Campus Map */}
          <div className="relative h-[500px] bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl overflow-hidden mb-6">
            {/* Grid overlay */}
            <div className="absolute inset-0 opacity-10">
              <div className="grid grid-cols-10 grid-rows-10 h-full">
                {[...Array(100)].map((_, i) => (
                  <div key={i} className="border border-gray-400" />
                ))}
              </div>
            </div>

            {/* Map Labels */}
            <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-lg shadow-sm">
              <p className="text-sm">Purdue University Campus</p>
            </div>

            {/* Study Locations */}
            {studyLocations.map((location) => (
              <motion.div
                key={location.id}
                className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer"
                style={{ left: `${location.x}%`, top: `${location.y}%` }}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: 1.1 }}
                onHoverStart={() => setHoveredLocation(location.id)}
                onHoverEnd={() => setHoveredLocation(null)}
              >
                {/* Heat Pulse Animation */}
                {location.hot && (
                  <motion.div
                    className={`absolute inset-0 bg-gradient-to-br ${getHeatIntensity(location.students)} rounded-full opacity-30 blur-xl`}
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [0.3, 0.1, 0.3],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                )}

                {/* Marker */}
                <div
                  className={`${getMarkerSize(location.students)} bg-gradient-to-br ${getHeatIntensity(location.students)} rounded-full flex items-center justify-center shadow-lg relative z-10`}
                >
                  <div className="text-white text-center">
                    <Users className="w-5 h-5 mx-auto mb-1" />
                    <div className="text-sm">{location.students}</div>
                  </div>
                </div>

                {/* Tooltip */}
                {hoveredLocation === location.id && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-black text-white px-4 py-2 rounded-lg text-sm whitespace-nowrap shadow-xl z-20"
                  >
                    <div className="font-semibold">{location.name}</div>
                    <div className="text-xs text-gray-300">{location.students} students studying</div>
                    <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-black rotate-45" />
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 text-sm flex-wrap">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-green-400 rounded-full" />
              <span className="text-gray-600">Low Activity (1-10)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-full" />
              <span className="text-gray-600">Medium Activity (11-25)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-full" />
              <span className="text-gray-600">High Activity (26+)</span>
            </div>
          </div>
        </div>

        {/* Location List */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <h3 className="mb-4">All Study Locations</h3>

          <div className="grid md:grid-cols-2 gap-4">
            {studyLocations
              .sort((a, b) => b.students - a.students)
              .map((location, index) => (
                <motion.div
                  key={location.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between p-4 rounded-xl border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 bg-gradient-to-br ${getHeatIntensity(location.students)} rounded-xl flex items-center justify-center text-white`}>
                      <MapPin className="w-6 h-6" />
                    </div>
                    <div>
                      <h4>{location.name}</h4>
                      <p className="text-sm text-gray-600 flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {location.students} students
                      </p>
                    </div>
                  </div>

                  {location.hot && (
                    <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs">
                      🔥 Hot Spot
                    </span>
                  )}
                </motion.div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
