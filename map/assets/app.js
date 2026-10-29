; (function ($, window, document, undefined) {
	'use strict';
	var GsapAnimate = (function () {
		var defaults = {
			mainDomAnime: false,
			scrollTonAnime: false,
			slideNavAnime: false,
			fixHeader: true,
			navMaxSreen: null,//导航咱开,
                         callback: null
		},
			options = {};

		return {
			init: function (opts) {
				options = $.extend(defaults, opts);
				//导航菜单下拉(放公共样式)
				const menuPer = document.querySelectorAll(".wp-navi .menu-item")

				if (options.mainDomAnime) {
					const dom = gsap.utils.toArray('.gsapdom')
					//模块动画
					dom.forEach((item) => {
						const position = item.getAttribute("gsap-position")
						const direction = item.getAttribute("gsap-direction") || ""
						const delay = item.getAttribute("delay") || ""
						const fix = item.getAttribute("fix") || "80%"
						const anim = gsap.from(item, {
							duration: 1, //动画执行时间
							ease: "power1.out",
							delay, //动画延迟时间
							opacity: "0",
							transform: direction == "X" || direction == "Y" ? `translate${direction}(${position}px)` : `${direction}(${position})`,
							scrollTrigger: {
								trigger: item, //监视区域
								//scrub: true,//擦洗
								start: `top ${fix}%`,
								// end: "bottom 70%",
								//toggleActions: "play none reverse none" //重置
							},
							onUpdate: (self) => {
								if (ScrollTrigger.isInViewport(item)) {
									if (options.callback) {
											options.callback(item)
										}
								} else {
									item.classList.remove("showdiv");
								}
							},
						})
					})
				}
				if (options.scrollTonAnime) {
					//top按钮
					gsap.from(".Scroll-to-top", {
						duration: 0.4, //动画执行时间
						opacity: "0",
						y: 200,
						scrollTrigger: {
							trigger: ".main1", //监视区域
							start: "top center",
							toggleActions: "play none none reset" //重置
						}
					})
				}
				if (options.slideNavAnime) {
					//侧导航
					gsap.to(".Quick-navigation", {
						duration: 0.4, //动画执行时间
						opacity: "1",
						x: 0,
						scrollTrigger: {
							trigger: ".main1", //监视区域
							start: "top center",
							toggleActions: "play none none reset" //重置
						}
					})
				}
				if (options.fixHeader) {
					//滚动导航固定在顶部(放公共样式)
					const headerEle = document.querySelector(options.fixHeader)
					var buttonAll = document.querySelectorAll(".main1 .tab-tt .title")

					// 滚动事件监听器  
					var isScrolling;
					document.addEventListener('scroll', function () {
						if (window.scrollY >= 500) {
							headerEle.style.position = 'fixed'
							headerEle.style.transform = 'translateY(0%)'
							headerEle.classList.add("fixed")
						} else if (window.scrollY < 500 && window.scrollY >= 250) {
							headerEle.style.transform = 'translateY(-250%)'
						} else {
							headerEle.style.position = 'absolute'
							headerEle.style.transform = 'translateY(0%)'
							headerEle.classList.remove("fixed")
						}
						isScrolling = true;

						// 禁用元素的鼠标事件  
						buttonAll.forEach(function (item) {
							item.style.pointerEvents = "none"
						})

						// 使用setTimeout来延迟检查滚动是否停止  
						clearTimeout(window.didScroll);
						window.didScroll = setTimeout(function () {
							isScrolling = false;

							// 滚动停止后恢复元素的鼠标事件  
							if (!isScrolling) {
								buttonAll.forEach(function (item) {
									item.style.pointerEvents = "auto"
								})
							}
						}, 66); // 延迟66ms，大约是一个滚动事件的间隔  
					})
				}
				if (options.navMaxSreen != null) {
					const c = options.navMaxSreen, a = GsapAnimate
					//大屏导航，根据属性data-fixnav-num排序(放公共样式)
					const mobileNavEle = document.querySelectorAll("[data-fixnav-num]")
					var _menu = []
					mobileNavEle.forEach(function (item) {
						const num = item.getAttribute("data-fixnav-num")
						_menu[num] = item.cloneNode(true)
					})
					_menu.forEach((el) => {
						document.querySelector(c.box).appendChild(el)
					})
					document.querySelector(c.control).addEventListener("click", function () {
						$(".fixbox").toggleClass("showNav")
						if (this.classList.contains("arrow")) {
							this.classList.remove("arrow")
							document.documentElement.style.overflow = 'auto';
							document.querySelector(options.fixHeader).classList.remove("fixopen")
						} else {
							this.classList.add("arrow")
							document.documentElement.style.overflow = 'hidden';
							document.querySelector(options.fixHeader).classList.add("fixopen")
						}
					})
					//手机端点击，二级导航下拉(放公共样式)

					document.querySelectorAll(".menu-switch-arrow").forEach((item) => {
						item.addEventListener("click", function () {
							if (item.classList.contains("open")) {
								gsap.to(item.nextElementSibling, {
									height: "0",
									opacity: 0
								})
								item.classList.remove("open")
							} else {
								item.classList.add("open")
								gsap.fromTo(item.nextElementSibling, {
									height: "0",
									opacity: 0
								}, {
									height: "auto",
									opacity: 1
								})
							}
						})
					})

				}
			},
			fixboxAlert: function (alertEle, duration = 0.5, fixhid = []) {
				var tl = gsap.timeline();
				const alertElement = document.querySelector(alertEle)
				const isMobile = window.innerWidth > 999 ? false : true
				//隐藏元素
				if (fixhid.length != 0) {
					fixhid.forEach((item) => {
						tl.to(item, {
							duration: 0.2, //动画执行时间
							autoAlpha: "0",
						}, "-=0.3")
					})
				}
				tl.to(alertElement, {
					transform: 'translateY(0)',
				})
				alertElement.childNodes.forEach((item) => {
					if (item.nodeType === 1)
						tl.fromTo(item, {
							y: 200,
							opacity: 0
						}, {
							y: 0,
							opacity: 1,
							duration
						}, "-=0.3")
				})
				document.documentElement.style.overflow = 'hidden';
				document.querySelector(options.fixHeader).classList.add("fixopen")
			},
			fixboxClose: function (closeEle, duration = 0.5, fixhid = []) {
				var t2 = gsap.timeline();
				const closeElement = document.querySelector(closeEle)
				Array.from(closeElement.childNodes).reverse().forEach((item) => {
					t2.fromTo(item, {
						y: 0,
						opacity: 1
					}, {
						y: 200,
						opacity: 0
					}, "-=0.3")
				})

				t2.to(closeElement, {
					transform: 'translateY(-100%)',
					duration,
				}, "-=0.3")
				//需要显示元素
				if (fixhid.length != 0) {
					fixhid.forEach((item) => {
						t2.to(item, {
							duration: 0, //动画执行时间
							autoAlpha: "1",
						}, "<")
					})
				}


			}
		}
	})();
	window.GsapAnimate = GsapAnimate;
})(jQuery, window, document);