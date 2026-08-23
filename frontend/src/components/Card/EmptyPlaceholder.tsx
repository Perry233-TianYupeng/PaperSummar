/** 无资料卡时的预留空白区（不显示内容，但进行空间预留）。 */

export function EmptyPlaceholder() {
  return (
    <div className="empty-placeholder">
      <div className="empty-placeholder-inner">
        <div className="empty-placeholder-title">PaperSummar</div>
        <div className="empty-placeholder-desc">
          当前还没有论文资料卡。
          <br />
          点击左侧「+新建资料卡」创建第一张卡片，开始搭建你的学术记忆库。
        </div>
      </div>
    </div>
  )
}
