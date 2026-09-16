/* 序引延航 · 内页共用脚本（2026 改版）：大导航、抽屉菜单、站内搜索、标题区纹样。与首页交互一致。 */
(function(){
  var nav=document.getElementById('sqh');
  if(!nav)return;
  var items=[].slice.call(nav.querySelectorAll('.sqh-mi'));
  var scrim=document.getElementById('sqh-scrim');
  var drawer=document.getElementById('sqh-drawer');
  var burger=nav.querySelector('.sqh-burger');
  var timer=null;
  var canHover=window.matchMedia&&window.matchMedia('(hover: hover)').matches;

  /* 市场地图页页眉上方还有数据条，遮罩和抽屉从页眉实际底边开始 */
  function below(){var b=Math.max(0,Math.round(nav.getBoundingClientRect().bottom))+'px';if(scrim)scrim.style.top=b;if(drawer)drawer.style.top=b;}

  function openItem(mi){
    items.forEach(function(x){var on=x===mi;x.classList.toggle('open',on);x.querySelector('.sqh-mt').setAttribute('aria-expanded',String(on));});
    if(mi)below();
    if(scrim)scrim.classList.toggle('on',!!mi);
  }
  items.forEach(function(mi){
    var bt=mi.querySelector('.sqh-mt'),q=mi.querySelector('.sqh-q');
    bt.addEventListener('click',function(){clearTimeout(timer);openItem(mi.classList.contains('open')?null:mi);if(q&&mi.classList.contains('open'))setTimeout(function(){q.focus();},60);});
    if(canHover&&!q){mi.addEventListener('mouseenter',function(){clearTimeout(timer);timer=setTimeout(function(){openItem(mi);},90);});}
  });
  if(canHover){
    nav.addEventListener('mouseenter',function(){clearTimeout(timer);});
    nav.addEventListener('mouseleave',function(){clearTimeout(timer);timer=setTimeout(function(){openItem(null);},200);});
  }
  if(scrim)scrim.addEventListener('click',function(){openItem(null);});
  nav.querySelectorAll('.sqh-mm a').forEach(function(a){a.addEventListener('click',function(){openItem(null);});});
  document.addEventListener('focusin',function(e){if(!nav.contains(e.target))openItem(null);});

  function closeDrawer(){if(!drawer)return;drawer.hidden=true;burger.setAttribute('aria-expanded','false');document.body.style.overflow='';}
  if(burger&&drawer){
    burger.addEventListener('click',function(){var open=drawer.hidden;if(open)below();drawer.hidden=!open;burger.setAttribute('aria-expanded',String(open));document.body.style.overflow=open?'hidden':'';});
    drawer.querySelectorAll('a').forEach(function(a){a.addEventListener('click',closeDrawer);});
    window.addEventListener('resize',function(){if(window.innerWidth>1080)closeDrawer();});
  }

  /* 当前栏目：洞察类页面、关于页 */
  var path=location.pathname;
  var sec=/\/(cases|briefs|report|markets|sources|nav)\//.test(path)?'ins':/\/about\//.test(path)?'about':'';
  if(sec){var cur=nav.querySelector('.sqh-mi[data-sec="'+sec+'"]');if(cur)cur.classList.add('is-current');}

  /* 站内搜索：站点有 Pagefind 索引时，直接在下拉面板里搜 */
  var searchItem=nav.querySelector('.sqh-mi[data-sec="search"]');
  var qIn=document.getElementById('sqh-q'),qBox=document.getElementById('sqh-qbox'),pfState=0;
  function pfInit(){
    if(typeof PagefindUI==='undefined')return false;
    new PagefindUI({element:'#sqh-qbox',showSubResults:true,showImages:false,translations:{placeholder:'搜索品牌拆解、报告、信号……',zero_results:'没有找到和「[SEARCH_TERM]」相关的内容'}});
    qIn.hidden=true;qBox.hidden=false;
    var inp=qBox.querySelector('input');if(inp)setTimeout(function(){inp.focus();},60);
    pfState=2;return true;
  }
  function pfLoad(){
    if(pfState)return;
    pfState=1;
    var css=document.createElement('link');css.rel='stylesheet';css.href='/pagefind/pagefind-ui.css';document.head.appendChild(css);
    var sc=document.createElement('script');sc.src='/pagefind/pagefind-ui.js';
    sc.onload=function(){if(!pfInit())pfState=3;};
    sc.onerror=function(){pfState=3;if(css.parentNode)css.parentNode.removeChild(css);};
    document.head.appendChild(sc);
  }
  if(searchItem&&qIn&&qBox){
    searchItem.querySelector('.sqh-mt').addEventListener('click',pfLoad);
    qIn.addEventListener('focus',pfLoad);
    qIn.addEventListener('keydown',function(e){if(e.key==='Enter'&&pfState===3){e.preventDefault();qIn.value='';qIn.placeholder='站内搜索还没开通，先看下面的常搜内容';}});
  }

  /* 页面自己有搜索框（市场地图、导航页）时，"/" 留给页面 */
  var pageHasSearch=!!document.querySelector('input#q');
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'){openItem(null);closeDrawer();}
    if(e.key==='/'&&!pageHasSearch&&searchItem&&!/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)&&window.innerWidth>1080){e.preventDefault();openItem(searchItem);setTimeout(function(){qIn.focus();},60);}
  });

  /* 标题区的等高线纹样（与首页同一画法） */
  function rings(cx,cy,count,gap){
    var o='';
    for(var k=0;k<count;k++){
      var r=40+k*gap,p=[];
      for(var i=0;i<=150;i++){var t=i/150*Math.PI*2,f=1+.08*Math.sin(3*t+.6+k*.17)+.05*Math.sin(5*t+1.7-k*.12)+.02*Math.sin(9*t+k*.3);p.push((cx+Math.cos(t)*r*f*1.3).toFixed(1)+','+(cy+Math.sin(t)*r*f*.84).toFixed(1));}
      o+='<polyline points="'+p.join(' ')+'" fill="none" stroke="#AEBBCE" stroke-opacity="'+(.17-k/count*.08).toFixed(3)+'" stroke-width="1"/>';
    }
    return o;
  }
  document.querySelectorAll('svg[data-engrave]').forEach(function(s){s.innerHTML=rings(1200,250,16,40);});

  /* 预览用：?menu=brand|svc|ins|about|search 打开对应的下拉 */
  try{var pm=new URLSearchParams(location.search).get('menu'),pt=pm&&document.getElementById('sqh-mm-'+pm);if(pt)openItem(pt.parentNode);}catch(e){}
})();
