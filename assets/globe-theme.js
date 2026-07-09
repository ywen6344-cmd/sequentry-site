/* ===================================================================
   序引 · 全站共用 3D 地球主题（单一真源）
   主页与市场地图页共用同一套「夜地球」观感：深色球体 + 蓝色密度渐变 + 大气光。
   依赖 globe.gl（window.Globe）；数据映射与交互由各页面自理。
   =================================================================== */
(function(){
  function lerp(a,b,t){
    const A=a.match(/\w\w/g).map(h=>parseInt(h,16)),B=b.match(/\w\w/g).map(h=>parseInt(h,16));
    return 'rgb('+A.map((v,i)=>Math.round(v+(B[i]-v)*t)).join(',')+')';
  }
  window.SQ_GLOBE={
    MATERIAL:'#0B1422',            /* 球体材质（暗夜海面） */
    ATMO:'#4076B8',                /* 大气光 */
    ATMO_ALT:.16,
    EMPTY:'#131C28',               /* 无数据国家：融入球体 */
    DIM:'#1C2A3F',                 /* 有数据但被筛掉：渐变最低档 */
    SIDE:'rgba(40,70,120,.22)',    /* 多边形侧面 */
    STROKE:'rgba(120,160,210,.3)', /* 国界描边 */
    SELECTED:'#4F9DF7',            /* 选中态高亮（渐变最高档） */
    ROTATE_SPEED:.5,
    PR_CAP:1.6,
    /* CSS：地球所在容器的深色舞台底（与主页 .stage 同款） */
    STAGE_BG:'radial-gradient(120% 95% at 34% 50%,#11203A 0%,#0A1424 56%,#070D18 100%)',
    /* 密度比例(0..1) → 蓝色渐变；开方拉开低密度档的区分度 */
    colorForRatio(r){return lerp('1C2A3F','4F9DF7',Math.min(1,Math.sqrt(Math.max(0,r))));},
    colorForCount(c,max){return c?this.colorForRatio(c/(max||1)):this.EMPTY;},
    altForCount(c,max){return c?0.006+Math.log(c+1)/Math.log((max||1)+1)*0.09:0.004;},
    /* 基础球体：透明背景 + 经纬网 + 大气 + 深色材质 + 自转（禁缩放，限像素比） */
    init(Globe,el,opts){
      opts=opts||{};
      const world=Globe({rendererConfig:opts.rendererConfig||{preserveDrawingBuffer:false}})(el)
        .backgroundColor('rgba(0,0,0,0)').showGlobe(true).showGraticules(true)
        .atmosphereColor(this.ATMO).atmosphereAltitude(this.ATMO_ALT)
        .pointOfView(opts.pov||{lat:25,lng:-55,altitude:2.3});
      world.globeImageUrl(null);
      const m=world.globeMaterial();
      if(m&&m.color)m.color.set(this.MATERIAL);
      if(m&&m.emissive)m.emissive.set(this.MATERIAL);
      world.controls().autoRotate=true;
      world.controls().autoRotateSpeed=this.ROTATE_SPEED;
      world.controls().enableZoom=false;
      if(world.renderer){const rd=world.renderer();if(rd&&rd.setPixelRatio)rd.setPixelRatio(Math.min(this.PR_CAP,window.devicePixelRatio||1));}
      return world;
    }
  };
})();
