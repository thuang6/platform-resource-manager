package main

type NaiveController struct {
	res       Resource
	cycThresh int
	cycCnt    int
}

func (c *NaiveController) update(bes []*Container, lcs []*Container, detected bool, hold bool) {
	if detected {
		c.cycCnt = 0
		if !c.res.isMinLevel() {
			c.res.setLevel(resLevMin)
			c.res.budgeting(bes, lcs)
		}
	} else {
		if !hold && !c.res.isFullLevel() {
			c.cycCnt++
			if c.cycCnt >= c.cycThresh {
				c.cycCnt = 0
				c.res.increaseLevel()
				c.res.budgeting(bes, lcs)
			}
		}
	}
}
