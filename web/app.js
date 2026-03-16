import React, { useState, useMemo, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import Papa from 'papaparse';

// --- IPA 坐标映射表 (舌位图标准坐标 0-1) ---
const VOWEL_MAP = {
  'i': [0, 0],   'y': [0.1, 0], 'u': [1, 0],   'ɯ': [0.9, 0],
  'e': [0, 0.3], 'ø': [0.1, 0.3],'o': [1, 0.3], 'ɤ': [0.9, 0.3],
  'ɛ': [0, 0.7], 'œ': [0.1, 0.7],'ɔ': [1, 0.7], 'ʌ': [0.9, 0.7],
  'a': [0, 1],   'æ': [0.2, 0.9],'ɑ': [1, 1],   'ɒ': [0.9, 1],
  'ə': [0.5, 0.5],'ɪ': [0.2, 0.15],'ʊ': [0.8, 0.15],
};

const DialectVisualizer = () => {
  const [data, setData] = useState([]);
  const [files, setFiles] = useState([]);
  const svgRef = useRef();

  // 处理文件上传
  const handleFileUpload = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    uploadedFiles.forEach(file => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const processed = results.data.map(d => ({
            ...d,
            originFile: file.name
          })).filter(d => d.读音);
          setData(prev => [...prev, ...processed]);
          setFiles(prev => [...new Set([...prev, file.name])]);
        }
      });
    });
  };

  // 数据预处理：拆分读音并计算坐标
  const plotPoints = useMemo(() => {
    const points = [];
    data.forEach(row => {
      const readings = row.读音.split('/');
      readings.forEach(r => {
        const cleanR = r.trim();
        if (!cleanR) return;
        
        // 判断是否为复元音 (长度大于1或包含特定组合)
        const isCompound = cleanR.length > 1;
        let coords = [0.5, 0.5];
        
        if (!isCompound && VOWEL_MAP[cleanR]) {
          coords = VOWEL_MAP[cleanR];
        }

        points.push({
          ...row,
          singleReading: cleanR,
          isCompound,
          coords,
          colorKey: row.韵
        });
      });
    });
    return points;
  }, [data]);

  // 绘图逻辑
  useEffect(() => {
    if (!plotPoints.length) return;

    const width = 800;
    const height = 500;
    const margin = { top: 40, right: 200, bottom: 40, left: 60 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // 颜色比例尺 (针对 韵)
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
      .domain([...new Set(plotPoints.map(d => d.韵))]);

    // --- 1. 单元音舌位图区域 (左侧梯形) ---
    const chartW = width - margin.left - margin.right;
    const chartH = height - margin.top - margin.bottom;
    
    const xMain = d3.scaleLinear().domain([0, 1]).range([margin.left, margin.left + chartW]);
    const yMain = d3.scaleLinear().domain([0, 1]).range([margin.top, margin.top + chartH]);

    // 绘制梯形背景
    const trapezoidPath = d3.line()([
      [xMain(0), yMain(0)], [xMain(1), yMain(0)],
      [xMain(1), yMain(1)], [xMain(0.5), yMain(1)], [xMain(0), yMain(0)]
    ]);

    svg.append("path")
      .attr("d", trapezoidPath)
      .attr("fill", "#f8fafc")
      .attr("stroke", "#cbd5e1")
      .attr("stroke-width", 2);

    // --- 2. 复元音展示区 (右侧) ---
    const compoundXStart = width - margin.right + 40;
    const compounds = plotPoints.filter(p => p.isCompound);
    const uniqueCompounds = [...new Set(compounds.map(p => p.singleReading))];
    const compoundScale = d3.scalePoint()
      .domain(uniqueCompounds)
      .range([margin.top, height - margin.bottom]);

    // --- 3. 绘制数据点 ---
    const g = svg.append("g");

    const dots = g.selectAll(".dot")
      .data(plotPoints)
      .enter()
      .append("g")
      .attr("class", "dot-group")
      .attr("transform", d => {
        if (d.isCompound) {
          return `translate(${compoundXStart}, ${compoundScale(d.singleReading)})`;
        }
        // 给单元音加一点随机抖动避免重叠
        return `translate(${xMain(d.coords[0]) + (Math.random()-0.5)*10}, ${yMain(d.coords[1]) + (Math.random()-0.5)*10})`;
      });

    // 绘制小圆点
    dots.append("circle")
      .attr("r", 4)
      .attr("fill", d => colorScale(d.韵))
      .attr("opacity", 0.7);

    // 绘制声组文本
    dots.append("text")
      .text(d => d.声组)
      .attr("x", 6)
      .attr("y", 4)
      .style("font-size", "10px")
      .style("fill", "#64748b");

    // 悬浮交互
    const tooltip = d3.select("#tooltip");
    dots.on("mouseover", (event, d) => {
      tooltip.style("opacity", 1)
        .html(`
          <div class="font-bold text-lg">${d.汉字}</div>
          <div>读音: ${d.singleReading}</div>
          <div>韵: ${d.韵}</div>
          <div>声组: ${d.声组}</div>
          <div>来源: ${d.point_name}</div>
        `)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px");
    }).on("mouseout", () => tooltip.style("opacity", 0));

    // 坐标轴标注
    svg.append("text").attr("x", margin.left).attr("y", margin.top - 10).text("前 High").style("font-size", "12px");
    svg.append("text").attr("x", margin.left + chartW).attr("y", margin.top - 10).text("后 High").attr("text-anchor", "end").style("font-size", "12px");
    svg.append("text").attr("x", compoundXStart).attr("y", margin.top - 10).text("复元音区").style("font-weight", "bold");

  }, [plotPoints]);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">吴语方言读音分布可视化系统</h1>
        
        <div className="mb-6 flex items-center gap-4">
          <input 
            type="file" 
            multiple 
            accept=".csv" 
            onChange={handleFileUpload}
            className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <div className="text-sm text-gray-400">
            已加载方言点: {files.join(', ') || '无'}
          </div>
        </div>

        <div className="relative border rounded-lg overflow-hidden bg-white">
          <svg ref={svgRef} width="100%" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid meet"></svg>
          <div 
            id="tooltip" 
            className="absolute pointer-events-none opacity-0 bg-white/90 border p-2 rounded shadow-xl text-sm transition-opacity z-10"
          ></div>
        </div>

        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="font-bold w-full mb-1">图例 (韵):</div>
          {[...new Set(plotPoints.map(p => p.韵))].map(y => (
            <div key={y} className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: d3.scaleOrdinal(d3.schemeCategory10).domain([...new Set(plotPoints.map(d => d.韵))])(y) }}></span>
              {y}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DialectVisualizer;